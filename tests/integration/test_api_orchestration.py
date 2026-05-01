from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.adapters.outbound.guardrails import NoOpGuardrailsAdapter
from app.application.usecase import MessageUseCase
from app.domain.models import RouterDecision
from app.main import createApp


class _StaticDegradedRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(
            route="knowledge",
            rationale="roteador-degradado-teste",
            degraded=True,
            usedModel=None,
            reply="Resposta estática do roteador (degradado).",
        )


class _NaoChamarConhecimento:
    def handleMessage(self, message: str) -> str:
        raise AssertionError("agente de conhecimento não deve ser chamado quando o roteador define reply")


class _EcoSuporteOrchestration:
    def handleMessage(self, message: str) -> str:
        return f"suporte:{message[:24]}"


class _EcoSwarmOrchestration:
    def handleMessage(self, message: str) -> str:
        return f"swarm:{message[:24]}"


def test_mensagens_usa_reply_estatico_do_roteador_sem_agente():
    use_case = MessageUseCase(
        knowledgeAgent=_NaoChamarConhecimento(),
        supportAgent=_EcoSuporteOrchestration(),
        swarmKnowledgeAgent=_EcoSwarmOrchestration(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_StaticDegradedRouter(),
    )
    client = TestClient(createApp(messageUseCase=use_case))
    response = client.post(
        "/messages",
        json={"message": "Qualquer pergunta", "userId": "orquestracao-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reply"] == "Resposta estática do roteador (degradado)."
    uuid.UUID(str(body["traceId"]))
    assert body.get("replySource") == "router"
    assert body.get("route") == "knowledge"
    assert body.get("agentModel") is None


class _RecordingRouter:
    def __init__(self) -> None:
        self.ultimaMensagem: str | None = None

    def decideRoute(self, message: str) -> RouterDecision:
        self.ultimaMensagem = message
        return RouterDecision(route="knowledge", rationale="eco")


class _EcoAgente:
    def handleMessage(self, message: str) -> str:
        return f"eco:{len(message)}"


def test_mensagens_encaminha_contexto_ao_roteador():
    router = _RecordingRouter()
    use_case = MessageUseCase(
        knowledgeAgent=_EcoAgente(),
        supportAgent=_EcoSuporteOrchestration(),
        swarmKnowledgeAgent=_EcoSwarmOrchestration(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=router,
    )
    client = TestClient(createApp(messageUseCase=use_case))
    texto = "Pergunta sobre maquininha Smart"
    response = client.post(
        "/messages",
        json={"message": texto, "userId": "orquestracao-2"},
    )
    assert response.status_code == 200
    assert router.ultimaMensagem == texto
    body = response.json()
    assert body["reply"] == f"eco:{len(texto)}"
    assert body.get("replySource") == "knowledge"
    assert body.get("route") == "knowledge"
