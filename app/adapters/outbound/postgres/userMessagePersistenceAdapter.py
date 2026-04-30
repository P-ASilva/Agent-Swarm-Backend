from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg

from app.domain.errors import PersistencyUnavailableError
from app.domain.models import GoogleIdentity, UserMessageRecord
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


@dataclass
class UserMessagePersistenceAdapter(UserMessagePersistencePort):
    databaseUrl: str = field(default_factory=_defaultSessionDatabaseUrl)

    @classmethod
    def fromEnv(cls) -> "UserMessagePersistenceAdapter":
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
                        SELECT user_request, model_answer, created_at
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
                userRequest=str(row[0]),
                modelAnswer=str(row[1]),
                createdAt=row[2],
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
