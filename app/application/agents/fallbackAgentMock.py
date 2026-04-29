from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports import AgentHandlerPort, OpenAiChatPort


@dataclass
class FallbackAgentMock(AgentHandlerPort):
    openAiChat: OpenAiChatPort | None = None

    def handleMessage(self, message: str) -> str:
        return f"Fallback agent answered: {message}"
