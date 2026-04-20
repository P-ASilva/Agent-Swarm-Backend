from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4


class MessageUseCase(Protocol):
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle inbound message payload and return response envelope fields."""


@dataclass
class DefaultMessageUseCase:
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload["message"]
        return {
            "status": "ok",
            "reply": f"Received: {message}",
            "trace_id": str(uuid4()),
        }

