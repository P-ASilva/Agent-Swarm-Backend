from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.models import GoogleIdentity, UserMessageRecord


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
