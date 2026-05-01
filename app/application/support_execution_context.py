from __future__ import annotations

from contextvars import ContextVar

supportConversationOwnerKeyContext: ContextVar[str | None] = ContextVar(
    "supportConversationOwnerKeyContext",
    default=None,
)
