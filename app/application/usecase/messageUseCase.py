from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.application.agents import FallbackAgentMock, KnowledgeAgentMock, SupportAgentMock
from app.domain.errors import PersistencyUnavailableError
from app.domain.models import RouterDecision, UserMessageRecord
from app.domain.ports import (
    AgentHandlerPort,
    GoogleTokenVerifierPort,
    MessageUseCasePort,
    RouterModelPort,
    UserMessagePersistencePort,
)


@dataclass
class MessageUseCase(MessageUseCasePort):
    routerModel: RouterModelPort | None = None
    knowledgeAgent: AgentHandlerPort | None = None
    supportAgent: AgentHandlerPort | None = None
    fallbackAgent: AgentHandlerPort | None = None
    googleTokenVerifier: GoogleTokenVerifierPort | None = None
    userMessagePersistence: UserMessagePersistencePort | None = None

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload["message"]
        clientUserLabel = str(payload.get("userId", "")).strip()
        if not clientUserLabel:
            clientUserLabel = "unknown"

        googleIdTokenRaw = payload.get("googleIdToken")
        hasGoogleToken = isinstance(googleIdTokenRaw, str) and bool(googleIdTokenRaw.strip())

        routerModel = self.routerModel or _UnavailableRouterModel()
        knowledgeAgent = self.knowledgeAgent or KnowledgeAgentMock()
        supportAgent = self.supportAgent or SupportAgentMock()
        fallbackAgent = self.fallbackAgent or FallbackAgentMock()
        traceId = str(uuid4())

        identity = None
        conversationOwnerKey = f"guest:{clientUserLabel}"

        if hasGoogleToken:
            if self.googleTokenVerifier is None or self.userMessagePersistence is None:
                raise PersistencyUnavailableError(
                    "Google-authenticated messages require a configured token verifier and "
                    "user-message persistence (SESSION_DATABASE_URL)."
                )
            identity = self.googleTokenVerifier.verifyIdToken(googleIdTokenRaw)
            conversationOwnerKey = f"google:{identity.subject}"

        contextualMessage = message
        if self.userMessagePersistence is not None:
            dayStart = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            dayEnd = dayStart + timedelta(days=1)
            history = self.userMessagePersistence.listMessagesForDay(
                conversationOwnerKey=conversationOwnerKey,
                dayStart=dayStart,
                dayEnd=dayEnd,
                limit=30,
            )
            contextualMessage = _buildMessageWithDailyContext(
                message=message,
                history=history,
                isGoogle=identity is not None,
            )

        decision = routerModel.decideRoute(contextualMessage)
        handlerByRoute: dict[str, AgentHandlerPort] = {
            "knowledge": knowledgeAgent,
            "support": supportAgent,
            "fallback": fallbackAgent,
        }
        selectedHandler = handlerByRoute[decision.route]
        reply = selectedHandler.handleMessage(contextualMessage)

        if self.userMessagePersistence is not None:
            self.userMessagePersistence.saveMessageTurn(
                conversationOwnerKey=conversationOwnerKey,
                googleIdentity=identity,
                clientUserLabel=clientUserLabel,
                userRequest=message,
                modelAnswer=reply,
                route=decision.route,
                traceId=traceId,
            )

        return {
            "status": "degraded" if decision.degraded else "ok",
            "reply": reply,
            "traceId": traceId,
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


def _buildMessageWithDailyContext(
    *,
    message: str,
    history: list[UserMessageRecord],
    isGoogle: bool,
) -> str:
    if not history:
        return message
    maxTurns = 8
    recent = history[-maxTurns:]
    contextLines: list[str] = []
    for index, turn in enumerate(recent, start=1):
        contextLines.append(f"{index}. user: {turn.userRequest}")
        contextLines.append(f"   assistant: {turn.modelAnswer}")
    contextBlock = "\n".join(contextLines)
    qualifier = "authenticated user" if isGoogle else "same client user identity"
    return (
        f"Conversation history from today ({qualifier}):\n"
        f"{contextBlock}\n\n"
        "Current user message:\n"
        f"{message}"
    )
