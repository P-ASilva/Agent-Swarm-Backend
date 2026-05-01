from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.application.agents import KnowledgeAgentMock, SupportAgentMock
from app.domain.errors import PersistencyUnavailableError
from app.domain.models import RouterDecision, UserMessageRecord
from app.domain.ports import (
    AgentHandlerPort,
    GoogleTokenVerifierPort,
    MessageUseCasePort,
    RouterModelPort,
    UserMessagePersistencePort,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageUseCase(MessageUseCasePort):
    routerModel: RouterModelPort | None = None
    knowledgeAgent: AgentHandlerPort | None = None
    supportAgent: AgentHandlerPort | None = None
    googleTokenVerifier: GoogleTokenVerifierPort | None = None
    userMessagePersistence: UserMessagePersistencePort | None = None

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload["message"]
        clientUserLabel = str(payload.get("userId", "")).strip()
        if not clientUserLabel:
            clientUserLabel = "unknown"

        logger.info("request received userId=%s messageLen=%d", clientUserLabel, len(message))

        googleIdTokenRaw = payload.get("googleIdToken")
        hasGoogleToken = isinstance(googleIdTokenRaw, str) and bool(googleIdTokenRaw.strip())

        routerModel = self.routerModel or _UnavailableRouterModel()
        knowledgeAgent = self.knowledgeAgent or KnowledgeAgentMock()
        supportAgent = self.supportAgent or SupportAgentMock()
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
        logger.info(
            "routing decision route=%s model=%s degraded=%s traceId=%s",
            decision.route,
            decision.usedModel,
            decision.degraded,
            traceId,
        )

        if decision.reply:
            reply = decision.reply
            logger.info("router static reply used traceId=%s", traceId)
        else:
            handlerByRoute: dict[str, AgentHandlerPort] = {
                "knowledge": knowledgeAgent,
                "support": supportAgent,
            }
            selectedHandler = handlerByRoute.get(decision.route, supportAgent)
            logger.info("dispatching agent=%s traceId=%s", decision.route, traceId)
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
            logger.info("turn persisted traceId=%s", traceId)

        return {
            "status": "degraded" if decision.degraded else "ok",
            "reply": reply,
            "traceId": traceId,
        }


class _UnavailableRouterModel(RouterModelPort):
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(
            route="knowledge",
            degraded=True,
            rationale="router-model-unavailable",
            usedModel=None,
            reply="Serviço temporariamente indisponível. Por favor, tente novamente.",
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
