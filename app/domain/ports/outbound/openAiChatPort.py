from __future__ import annotations

from typing import Any, Protocol


class OpenAiChatPort(Protocol):
    def chatCompletion(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.0,
        responseFormat: dict[str, Any] | None = None,
    ) -> str:
        """Run OpenAI chat completion and return text content."""
