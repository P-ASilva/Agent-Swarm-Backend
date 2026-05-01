from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.domain.models import SupportOperation, TurnDeletionSpecification
from app.domain.ports import UserMessagePersistencePort

logger = logging.getLogger(__name__)

_ALLOWED_PROFILE_KEYS = frozenset({"display_name", "profile_metadata"})


@dataclass
class SupportOperationsExecutor:
    userMessagePersistence: UserMessagePersistencePort | None

    def run(self, *, conversationOwnerKey: str, operations: tuple[SupportOperation, ...]) -> None:
        if self.userMessagePersistence is None:
            logger.info("support tools skipped persistence=none opsCount=%s", len(operations))
            return

        for op in operations:
            if op.kind == "noop":
                continue
            if op.kind == "profile_patch":
                self._applyProfilePatch(conversationOwnerKey=conversationOwnerKey, payload=op.payload)
            elif op.kind == "delete_turns":
                self._applyDeletes(conversationOwnerKey=conversationOwnerKey, payload=op.payload)

    def _applyProfilePatch(self, *, conversationOwnerKey: str, payload: dict[str, Any]) -> None:
        extraKeys = frozenset(payload.keys()) - _ALLOWED_PROFILE_KEYS
        if extraKeys:
            logger.info(
                "support profile_patch skipped unknown keys count=%s",
                len(extraKeys),
            )

        dnRaw = payload.get("display_name")
        displayName = dnRaw.strip() if isinstance(dnRaw, str) else None
        if displayName == "":
            displayName = None

        metaRaw = payload.get("profile_metadata")
        metadataPatch: dict[str, Any] | None = None
        if metaRaw is not None:
            if not isinstance(metaRaw, dict):
                logger.info("support profile_patch ignored non-object profile_metadata")
            else:
                metadataPatch = dict(metaRaw)

        if displayName is None and metadataPatch is None:
            logger.info("support profile_patch noop no effective fields")
            return

        self.userMessagePersistence.upsertConversationProfile(
            conversationOwnerKey=conversationOwnerKey,
            displayName=displayName,
            metadataPatch=metadataPatch,
        )
        logger.info(
            "support tool executed kind=profile_patch patchFields=%s",
            ",".join(
                k for k in ("display_name", "profile_metadata") if payload.get(k) is not None
            )
            or "none",
        )

    def _applyDeletes(self, *, conversationOwnerKey: str, payload: dict[str, Any]) -> None:
        scope = payload.get("scope")
        if not isinstance(scope, str):
            logger.info("support delete_turns skipped missing scope")
            return
        normalized = scope.strip().lower()

        try:
            if normalized == "all":
                spec = TurnDeletionSpecification(kind="all")
            elif normalized == "by_trace_ids":
                ids = payload.get("trace_ids")
                if not isinstance(ids, list) or not ids:
                    logger.info("support delete_turns by_trace_ids skipped empty")
                    return
                traceTuples = tuple(str(x).strip() for x in ids if str(x).strip())
                spec = TurnDeletionSpecification(kind="by_trace_ids", traceIds=traceTuples)
            elif normalized == "by_turn_ids":
                ids = payload.get("turn_ids")
                if not isinstance(ids, list) or not ids:
                    logger.info("support delete_turns by_turn_ids skipped empty")
                    return
                turnTuples = tuple(str(x).strip() for x in ids if str(x).strip())
                spec = TurnDeletionSpecification(kind="by_turn_ids", turnIds=turnTuples)
            else:
                logger.info("support delete_turns unsupported scope=%s", normalized[:32])
                return

            deleted = self.userMessagePersistence.deleteMessageTurns(
                conversationOwnerKey=conversationOwnerKey,
                specification=spec,
            )
            logger.info(
                "support tool executed kind=delete_turns scope=%s deleted=%s",
                normalized,
                deleted,
            )
        except ValueError as exc:
            logger.info(
                "support delete_turns validation failed error=%s",
                type(exc).__name__,
            )
