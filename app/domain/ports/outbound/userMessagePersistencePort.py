from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.domain.models import (
    ConversationProfileSnapshot,
    GoogleIdentity,
    TurnDeletionSpecification,
    UserMessageRecord,
)


class UserMessagePersistencePort(Protocol):
    def listMessagesForDay(
        self,
        *,
        conversationOwnerKey: str,
        dayStart: datetime,
        dayEnd: datetime,
        limit: int = 30,
    ) -> list[UserMessageRecord]:
        """Load persisted conversation turns for the same logical user for the date range."""

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
        """Persist one user request + model answer; googleIdentity is set when authenticated via Google."""

    def getConversationProfile(self, *, conversationOwnerKey: str) -> ConversationProfileSnapshot:
        ...

    def upsertConversationProfile(
        self,
        *,
        conversationOwnerKey: str,
        displayName: str | None = None,
        metadataPatch: dict[str, Any] | None = None,
    ) -> None:
        ...

    def deleteMessageTurns(
        self,
        *,
        conversationOwnerKey: str,
        specification: TurnDeletionSpecification,
    ) -> int:
        """Hard-delete turns scoped to owner key; returns count of deleted rows."""
