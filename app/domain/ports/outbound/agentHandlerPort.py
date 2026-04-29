from __future__ import annotations

from typing import Protocol


class AgentHandlerPort(Protocol):
    def handleMessage(self, message: str) -> str:
        """Return deterministic or generated answer for the message."""
