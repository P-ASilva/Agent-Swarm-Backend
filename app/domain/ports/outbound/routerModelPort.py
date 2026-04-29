from __future__ import annotations

from typing import Protocol

from app.domain.models import RouterDecision


class RouterModelPort(Protocol):
    def decideRoute(self, message: str) -> RouterDecision:
        """Decide which downstream agent should answer the message."""
