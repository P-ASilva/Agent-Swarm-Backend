from __future__ import annotations

import pytest

from app.adapters.outbound.guardrails import RuleBasedGuardrailsAdapter
from app.application.usecase import MessageUseCase
from app.domain.models import GuardrailVerdict, RouterDecision


class CountingRouter:
    def __init__(self) -> None:
        self.calls = 0
        self.lastMessage: str | None = None

    def decideRoute(self, message: str) -> RouterDecision:
        self.calls += 1
        self.lastMessage = message
        return RouterDecision(route="knowledge", rationale="test-router")


class EchoKnowledgeAgent:
    def handleMessage(self, message: str) -> str:
        return f"réplica:{message}"


class BlockInputGuardrailStub:
    def evaluateInput(
        self,
        contextualMessage: str,
        *,
        conversationOwnerKey: str,
        clientUserLabel: str,
        hasGoogleIdentity: bool,
    ) -> GuardrailVerdict:
        del contextualMessage, conversationOwnerKey, clientUserLabel, hasGoogleIdentity
        return GuardrailVerdict(allowed=False, reply="bloqueado-entrada", auditCode="stub_block_in")

    def evaluateOutput(
        self,
        reply: str,
        *,
        route: str,
        conversationOwnerKey: str,
    ) -> GuardrailVerdict:
        del reply, route, conversationOwnerKey
        return GuardrailVerdict(allowed=True, auditCode="noop")


class RewriteInputGuardrailStub:
    def evaluateInput(
        self,
        contextualMessage: str,
        *,
        conversationOwnerKey: str,
        clientUserLabel: str,
        hasGoogleIdentity: bool,
    ) -> GuardrailVerdict:
        del contextualMessage, conversationOwnerKey, clientUserLabel, hasGoogleIdentity
        return GuardrailVerdict(
            allowed=True,
            rewrittenMessage="texto-substituido-pelo-guardrail",
            auditCode="stub_rewrite",
        )

    def evaluateOutput(
        self,
        reply: str,
        *,
        route: str,
        conversationOwnerKey: str,
    ) -> GuardrailVerdict:
        del reply, route, conversationOwnerKey
        return GuardrailVerdict(allowed=True, auditCode="noop")


@pytest.mark.asyncio
async def test_input_block_skips_router_and_uses_safe_reply():
    router = CountingRouter()
    useCase = MessageUseCase(
        routerModel=router,
        knowledgeAgent=EchoKnowledgeAgent(),
        messageGuardrails=BlockInputGuardrailStub(),
    )
    result = await useCase.execute({"message": "hello", "userId": "g1"})
    assert router.calls == 0
    assert result["reply"] == "bloqueado-entrada"
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_input_rewrite_passes_altered_text_to_router():
    router = CountingRouter()
    useCase = MessageUseCase(
        routerModel=router,
        knowledgeAgent=EchoKnowledgeAgent(),
        messageGuardrails=RewriteInputGuardrailStub(),
    )
    result = await useCase.execute({"message": "hello", "userId": "g2"})
    assert router.calls == 1
    assert router.lastMessage == "texto-substituido-pelo-guardrail"
    assert result["reply"] == "réplica:texto-substituido-pelo-guardrail"


@pytest.mark.asyncio
async def test_without_guardrails_router_sees_raw_message():
    router = CountingRouter()
    useCase = MessageUseCase(
        routerModel=router,
        knowledgeAgent=EchoKnowledgeAgent(),
        messageGuardrails=None,
    )
    result = await useCase.execute({"message": "raw-direct", "userId": "g3"})
    assert router.calls == 1
    assert router.lastMessage == "raw-direct"
    assert result["reply"] == "réplica:raw-direct"


@pytest.mark.asyncio
async def test_output_guardrail_replaces_reply():
    router = CountingRouter()
    guard = RuleBasedGuardrailsAdapter(outputBlockedSubstrings=("secret-token",))
    useCase = MessageUseCase(
        routerModel=router,
        knowledgeAgent=EchoKnowledgeAgent(),
        messageGuardrails=guard,
    )
    result = await useCase.execute({"message": "x secret-token y", "userId": "g4"})
    assert router.calls == 1
    assert "secret-token" not in result["reply"]
    assert "limitada por políticas" in result["reply"]
