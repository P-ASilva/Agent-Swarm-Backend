from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.application.support_execution_context import supportConversationOwnerKeyContext
from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER
from app.domain.errors import PersistencyUnavailableError
from app.domain.models import GoogleIdentity, RouterDecision, UserMessageRecord
from app.domain.ports import (
    AgentHandlerPort,
    GoogleTokenVerifierPort,
    MessageGuardrailsPort,
    MessageUseCasePort,
    RouterModelPort,
    UserMessagePersistencePort,
)

logger = logging.getLogger(__name__)

_INPUT_GUARD_FALLBACK_REPLY = (
    "Não posso processar esta mensagem. Reformule ou tente novamente."
)


@dataclass
class MessageUseCase(MessageUseCasePort):
    knowledgeAgent: AgentHandlerPort
    supportAgent: AgentHandlerPort
    swarmKnowledgeAgent: AgentHandlerPort
    routerModel: RouterModelPort | None = None
    googleTokenVerifier: GoogleTokenVerifierPort | None = None
    userMessagePersistence: UserMessagePersistencePort | None = None
    messageGuardrails: MessageGuardrailsPort | None = None
    knowledgeModelLabel: str | None = None
    supportModelLabel: str | None = None
    swarmKnowledgeLabel: str | None = None

    def _clientConversationAndIdentity(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, str, GoogleIdentity | None]:
        clientUserLabel = str(payload.get("userId", "")).strip()
        if not clientUserLabel:
            clientUserLabel = "unknown"
        googleIdTokenRaw = payload.get("googleIdToken")
        hasGoogleToken = isinstance(googleIdTokenRaw, str) and bool(googleIdTokenRaw.strip())
        identity: GoogleIdentity | None = None
        conversationOwnerKey = f"guest:{clientUserLabel}"
        if hasGoogleToken:
            if self.googleTokenVerifier is None or self.userMessagePersistence is None:
                raise PersistencyUnavailableError(
                    "Mensagens autenticadas com Google exigem verificador de token e "
                    "persistência de mensagens configurados (SESSION_DATABASE_URL)."
                )
            identity = self.googleTokenVerifier.verifyIdToken(googleIdTokenRaw)
            conversationOwnerKey = f"google:{identity.subject}"
        return clientUserLabel, conversationOwnerKey, identity

    async def listTodayHistory(self, payload: dict[str, Any]) -> dict[str, Any]:
        _clientUserLabel, conversationOwnerKey, _identity = self._clientConversationAndIdentity(payload)
        if self.userMessagePersistence is None:
            return {"turns": []}
        dayStart = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        dayEnd = dayStart + timedelta(days=1)
        rows = self.userMessagePersistence.listMessagesForDay(
            conversationOwnerKey=conversationOwnerKey,
            dayStart=dayStart,
            dayEnd=dayEnd,
            limit=30,
        )
        turns = [
            {
                "turnId": row.turnId or "",
                "traceId": row.traceId or "",
                "userRequest": row.userRequest,
                "modelAnswer": row.modelAnswer,
                "createdAt": row.createdAt.isoformat(),
            }
            for row in rows
        ]
        logger.info(
            "history listed ownerKeyPrefix=%s turns=%d",
            conversationOwnerKey.split(":", maxsplit=1)[0],
            len(turns),
        )
        return {"turns": turns}

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload["message"]
        clientUserLabel, conversationOwnerKey, identity = self._clientConversationAndIdentity(payload)

        logger.info("request received userId=%s messageLen=%d", clientUserLabel, len(message))

        routerModel = self.routerModel or _UnavailableRouterModel()
        traceId = str(uuid4())

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

        blockedByInput = False
        decision: RouterDecision | None = None
        reply: str | None = None
        agentInvoked = False

        if self.messageGuardrails is not None:
            inputVerdict = self.messageGuardrails.evaluateInput(
                contextualMessage,
                conversationOwnerKey=conversationOwnerKey,
                clientUserLabel=clientUserLabel,
                hasGoogleIdentity=identity is not None,
            )
            logger.info(
                "guardrail input outcome=%s audit=%s traceId=%s",
                "allowed" if inputVerdict.allowed else "blocked",
                inputVerdict.auditCode,
                traceId,
            )
            if not inputVerdict.allowed:
                blockedByInput = True
                reply = (inputVerdict.reply or _INPUT_GUARD_FALLBACK_REPLY).strip() or _INPUT_GUARD_FALLBACK_REPLY
                decision = RouterDecision(
                    route="knowledge",
                    rationale=f"guardrail:{inputVerdict.auditCode}",
                    usedModel=None,
                    degraded=inputVerdict.degraded,
                    reply=None,
                )
            elif inputVerdict.rewrittenMessage is not None:
                contextualMessage = inputVerdict.rewrittenMessage

        if not blockedByInput:
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
                agentInvoked = True
                routed = decision.route
                logger.info("dispatching agent=%s traceId=%s", routed, traceId)
                if routed == "knowledge":
                    reply = self.knowledgeAgent.handleMessage(contextualMessage)
                elif routed == "swarm":
                    reply = self.swarmKnowledgeAgent.handleMessage(contextualMessage)
                else:
                    token = supportConversationOwnerKeyContext.set(conversationOwnerKey)
                    try:
                        reply = self.supportAgent.handleMessage(contextualMessage)
                    finally:
                        supportConversationOwnerKeyContext.reset(token)

        assert decision is not None
        assert reply is not None

        outputDegradedExtra = False
        if self.messageGuardrails is not None:
            outputVerdict = self.messageGuardrails.evaluateOutput(
                reply,
                route=decision.route,
                conversationOwnerKey=conversationOwnerKey,
            )
            logger.info(
                "guardrail output outcome=%s audit=%s traceId=%s",
                "allowed" if outputVerdict.allowed else "blocked",
                outputVerdict.auditCode,
                traceId,
            )
            if not outputVerdict.allowed and outputVerdict.reply:
                reply = outputVerdict.reply.strip() or reply
                outputDegradedExtra = outputVerdict.degraded

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

        envelopeDegraded = bool(decision.degraded or outputDegradedExtra)
        if blockedByInput:
            reply_source = "guardrail"
            agent_model: str | None = None
        elif not agentInvoked:
            reply_source = "router"
            agent_model = None
        elif decision.route == "knowledge":
            reply_source = "knowledge"
            agent_model = self.knowledgeModelLabel
        elif decision.route == "swarm":
            reply_source = "swarm"
            agent_model = self.swarmKnowledgeLabel
        else:
            reply_source = "support"
            agent_model = self.supportModelLabel

        return {
            "status": "degraded" if envelopeDegraded else "ok",
            "reply": reply,
            "traceId": traceId,
            "route": decision.route,
            "routerModel": decision.usedModel,
            "agentModel": agent_model,
            "replySource": reply_source,
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
        tid = turn.traceId if turn.traceId else "-"
        tuid = turn.turnId if turn.turnId else "-"
        contextLines.append(f"{index}. traceId={tid} turnId={tuid}")
        contextLines.append(f"   usuário: {turn.userRequest}")
        contextLines.append(f"   assistente: {turn.modelAnswer}")
    contextBlock = "\n".join(contextLines)
    qualifier = "usuário autenticado" if isGoogle else "mesma identidade de usuário convidado"
    return (
        f"Histórico da conversa de hoje ({qualifier}):\n"
        f"{contextBlock}"
        f"{FULL_CURRENT_USER_MESSAGE_LEADER}{message}"
    )
