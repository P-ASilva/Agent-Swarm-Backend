from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports import AgentHandlerPort


@dataclass
class SwarmKnowledgeAgentMock(AgentHandlerPort):
    def handleMessage(self, message: str) -> str:
        del message
        return "guia-swarm:mock"
