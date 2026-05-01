from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConversationProfileSnapshot:
    conversationOwnerKey: str
    displayName: str | None
    metadata: dict[str, Any]
