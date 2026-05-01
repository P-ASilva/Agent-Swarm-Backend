from __future__ import annotations

from typing import Any, Protocol


class MessageUseCasePort(Protocol):
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle inbound message payload and return response envelope fields."""

    async def listTodayHistory(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return today's persisted turns for the resolved conversation owner key."""
