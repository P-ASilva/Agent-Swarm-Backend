from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg

from app.domain.errors import PersistencyUnavailableError
from app.domain.models import (
    ConversationProfileSnapshot,
    GoogleIdentity,
    TurnDeletionSpecification,
    UserMessageRecord,
)
from app.domain.ports import UserMessagePersistencePort

_PERSISTENCY_HINT = (
    "User message database is unavailable or migrations were not applied. "
    "Run: python -m message_persistence.cli migrate"
)


def _defaultSessionDatabaseUrl() -> str:
    return os.getenv(
        "SESSION_DATABASE_URL",
        "postgresql://session_swarm:session_swarm@localhost:5433/session_swarm",
    )


def _validateDeletionSpec(spec: TurnDeletionSpecification) -> None:
    if spec.kind == "by_turn_ids" and not spec.turnIds:
        raise ValueError("TurnDeletionSpecification.by_turn_ids requires non-empty turnIds.")
    if spec.kind == "by_trace_ids" and not spec.traceIds:
        raise ValueError("TurnDeletionSpecification.by_trace_ids requires non-empty traceIds.")

    if spec.kind == "by_turn_ids":
        for tid in spec.turnIds:
            try:
                uuid.UUID(str(tid))
            except ValueError as exc:
                raise ValueError(f"invalid turn id format: {tid}") from exc


def _normalizeUuidList(ids: tuple[str, ...]) -> list[uuid.UUID]:
    return [uuid.UUID(str(raw)) for raw in ids]


def _mergeMetadataJson(existing: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    if patch is None:
        return dict(existing)
    merged = dict(existing)
    merged.update(patch)
    return merged


@dataclass
class UserMessagePersistenceAdapter(UserMessagePersistencePort):
    databaseUrl: str = field(default_factory=_defaultSessionDatabaseUrl)

    @classmethod
    def fromEnv(cls) -> UserMessagePersistenceAdapter:
        return cls(databaseUrl=_defaultSessionDatabaseUrl())

    def listMessagesForDay(
        self,
        *,
        conversationOwnerKey: str,
        dayStart: datetime,
        dayEnd: datetime,
        limit: int = 30,
    ) -> list[UserMessageRecord]:
        try:
            with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id::text,
                               trace_id,
                               user_request,
                               model_answer,
                               created_at
                        FROM user_message_turns
                        WHERE conversation_owner_key = %s
                          AND created_at >= %s
                          AND created_at < %s
                        ORDER BY created_at ASC
                        LIMIT %s
                        """,
                        (conversationOwnerKey, dayStart, dayEnd, limit),
                    )
                    rows = cursor.fetchall()
        except psycopg.Error as exc:
            raise PersistencyUnavailableError(_PERSISTENCY_HINT) from exc
        return [
            UserMessageRecord(
                userRequest=str(row[2]),
                modelAnswer=str(row[3]),
                createdAt=row[4],
                turnId=str(row[0]),
                traceId=str(row[1]),
            )
            for row in rows
        ]

    def saveMessageTurn(
        self,
        *,
        conversationOwnerKey: str,
        googleIdentity: GoogleIdentity | None,
        clientUserLabel: str,
        userRequest: str,
        modelAnswer: str,
        route: str,
        traceId: str,
    ) -> None:
        try:
            with psycopg.connect(self.databaseUrl, autocommit=False) as connection:
                with connection.cursor() as cursor:
                    linkedUserPk: str | None = None
                    if googleIdentity is not None:
                        linkedUserPk = self._upsertUser(cursor=cursor, identity=googleIdentity)
                    cursor.execute(
                        """
                        INSERT INTO user_message_turns (
                            id,
                            user_id,
                            conversation_owner_key,
                            client_user_label,
                            user_request,
                            model_answer,
                            routed_agent,
                            trace_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            linkedUserPk,
                            conversationOwnerKey,
                            clientUserLabel,
                            userRequest,
                            modelAnswer,
                            route,
                            traceId,
                        ),
                    )
                connection.commit()
        except psycopg.Error as exc:
            raise PersistencyUnavailableError(_PERSISTENCY_HINT) from exc

    def getConversationProfile(self, *, conversationOwnerKey: str) -> ConversationProfileSnapshot:
        try:
            with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT display_name,
                               COALESCE(metadata_json, '{}'::jsonb)
                        FROM conversation_profiles
                        WHERE conversation_owner_key = %s
                        """,
                        (conversationOwnerKey,),
                    )
                    row = cursor.fetchone()
        except psycopg.Error as exc:
            raise PersistencyUnavailableError(_PERSISTENCY_HINT) from exc

        if row is None:
            return ConversationProfileSnapshot(
                conversationOwnerKey=conversationOwnerKey,
                displayName=None,
                metadata={},
            )
        meta = row[1]
        if not isinstance(meta, dict):
            meta = {}
        return ConversationProfileSnapshot(
            conversationOwnerKey=conversationOwnerKey,
            displayName=row[0],
            metadata=meta,
        )

    def upsertConversationProfile(
        self,
        *,
        conversationOwnerKey: str,
        displayName: str | None = None,
        metadataPatch: dict[str, Any] | None = None,
    ) -> None:
        try:
            with psycopg.connect(self.databaseUrl, autocommit=False) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT display_name,
                               COALESCE(metadata_json, '{}'::jsonb)
                        FROM conversation_profiles
                        WHERE conversation_owner_key = %s
                        """,
                        (conversationOwnerKey,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        newDisplay = displayName
                        newMeta = dict(metadataPatch) if metadataPatch is not None else {}
                    else:
                        curDisplay = row[0]
                        curMeta: dict[str, Any] = row[1] if isinstance(row[1], dict) else {}
                        newDisplay = displayName if displayName is not None else curDisplay
                        newMeta = _mergeMetadataJson(curMeta, metadataPatch)

                    cursor.execute(
                        """
                        INSERT INTO conversation_profiles (
                            conversation_owner_key,
                            display_name,
                            metadata_json,
                            updated_at
                        )
                        VALUES (%s, %s, %s::jsonb, NOW())
                        ON CONFLICT (conversation_owner_key) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            metadata_json = EXCLUDED.metadata_json,
                            updated_at = NOW()
                        """,
                        (
                            conversationOwnerKey,
                            newDisplay,
                            json.dumps(newMeta),
                        ),
                    )
                connection.commit()
        except psycopg.Error as exc:
            raise PersistencyUnavailableError(_PERSISTENCY_HINT) from exc

    def deleteMessageTurns(
        self,
        *,
        conversationOwnerKey: str,
        specification: TurnDeletionSpecification,
    ) -> int:
        _validateDeletionSpec(specification)
        try:
            with psycopg.connect(self.databaseUrl, autocommit=False) as connection:
                with connection.cursor() as cursor:
                    deleted = 0
                    if specification.kind == "all":
                        cursor.execute(
                            """
                            DELETE FROM user_message_turns
                            WHERE conversation_owner_key = %s
                            """,
                            (conversationOwnerKey,),
                        )
                        deleted = cursor.rowcount
                    elif specification.kind == "by_turn_ids":
                        idList = _normalizeUuidList(specification.turnIds)
                        cursor.execute(
                            """
                            DELETE FROM user_message_turns
                            WHERE conversation_owner_key = %s
                              AND id = ANY(%s::uuid[])
                            """,
                            (conversationOwnerKey, idList),
                        )
                        deleted = cursor.rowcount
                    else:
                        cursor.execute(
                            """
                            DELETE FROM user_message_turns
                            WHERE conversation_owner_key = %s
                              AND trace_id = ANY(%s::text[])
                            """,
                            (conversationOwnerKey, list(specification.traceIds)),
                        )
                        deleted = cursor.rowcount
                connection.commit()
        except psycopg.Error as exc:
            raise PersistencyUnavailableError(_PERSISTENCY_HINT) from exc

        return int(deleted)

    def _upsertUser(self, *, cursor: psycopg.Cursor[Any], identity: GoogleIdentity) -> str:
        candidateId = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO app_users (
                id,
                google_subject,
                email,
                issuer,
                audience
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (google_subject)
            DO UPDATE SET
                email = EXCLUDED.email,
                issuer = EXCLUDED.issuer,
                audience = EXCLUDED.audience,
                updated_at = NOW()
            RETURNING id::text
            """,
            (
                candidateId,
                identity.subject,
                identity.email,
                identity.issuer,
                identity.audience,
            ),
        )
        return str(cursor.fetchone()[0])
