from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.application.agents import FallbackAgentMock, KnowledgeAgentMock, SupportAgentMock
from app.domain.models import RouterDecision
from app.domain.ports import AgentHandlerPort, MessageUseCasePort, RouterModelPort


@dataclass
class DefaultMessageUseCase(MessageUseCasePort):
    routerModel: RouterModelPort | None = None
    knowledgeAgent: AgentHandlerPort | None = None
    supportAgent: AgentHandlerPort | None = None
    fallbackAgent: AgentHandlerPort | None = None

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload["message"]
        routerModel = self.routerModel or _UnavailableRouterModel()
        knowledgeAgent = self.knowledgeAgent or KnowledgeAgentMock()
        supportAgent = self.supportAgent or SupportAgentMock()
        fallbackAgent = self.fallbackAgent or FallbackAgentMock()

        decision = routerModel.decideRoute(message)
        handlerByRoute: dict[str, AgentHandlerPort] = {
            "knowledge": knowledgeAgent,
            "support": supportAgent,
            "fallback": fallbackAgent,
        }
        selectedHandler = handlerByRoute[decision.route]
        reply = selectedHandler.handleMessage(message)

        return {
            "status": "degraded" if decision.degraded else "ok",
            "reply": reply,
            "traceId": str(uuid4()),
        }


class _UnavailableRouterModel(RouterModelPort):
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(
            route="fallback",
            degraded=True,
            rationale="router-model-unavailable",
            usedModel=None,
        )
