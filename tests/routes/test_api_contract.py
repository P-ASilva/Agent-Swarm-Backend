from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.adapters.outbound.guardrails import NoOpGuardrailsAdapter
from app.application.usecase import MessageUseCase
from app.domain.models import (
    ConversationProfileSnapshot,
    GoogleIdentity,
    RouterDecision,
    UserMessageRecord,
)
from app.domain.ports import InvalidGoogleTokenError
from app.main import createApp


class _FixedRouteRouter:
    def __init__(self, route: str) -> None:
        self.route = route

    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route=self.route, rationale="teste-contrato")


class _EchoKnowledge:
    def handleMessage(self, message: str) -> str:
        return f"conhecimento:{message[:48]}"


class _EchoSupport:
    def handleMessage(self, message: str) -> str:
        return f"suporte:{message[:48]}"


class _EchoSwarm:
    def handleMessage(self, message: str) -> str:
        return f"swarm:{message[:48]}"


def _make_client(use_case: MessageUseCase) -> TestClient:
    return TestClient(createApp(messageUseCase=use_case))


def test_health_retorna_ok():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
    )
    client = _make_client(use_case)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_messages_200_com_envelope_obrigatorio():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages",
        json={"message": "Qual é a taxa do Pix?", "userId": "usuario-contrato-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert isinstance(body.get("reply"), str) and body["reply"].strip()
    uuid.UUID(str(body["traceId"]))


def test_post_messages_suporte_quando_rota_support():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("support"),
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages",
        json={"message": "Não consigo fazer login na minha conta.", "userId": "usuario-contrato-2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"].startswith("suporte:")


def test_post_messages_swarm_quando_rota_swarm():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("swarm"),
        swarmKnowledgeLabel="test-swarm-label",
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages",
        json={"message": "Como funciona o roteador deste swarm?", "userId": "usuario-contrato-swarm"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"].startswith("swarm:")
    assert body.get("route") == "swarm"
    assert body.get("replySource") == "swarm"
    assert body.get("agentModel") == "test-swarm-label"


def test_post_messages_payload_vazio_retorna_422():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
    )
    client = _make_client(use_case)
    response = client.post("/messages", json={})
    assert response.status_code == 422


class _HistoryPersistenceStub:
    def __init__(self, rows: list[UserMessageRecord]) -> None:
        self.rows = rows
        self.lastOwnerKey: str | None = None

    def listMessagesForDay(
        self,
        *,
        conversationOwnerKey: str,
        dayStart: datetime,
        dayEnd: datetime,
        limit: int = 30,
    ):
        del dayStart, dayEnd, limit
        self.lastOwnerKey = conversationOwnerKey
        return list(self.rows)

    def saveMessageTurn(self, **kwargs):
        del kwargs

    def getConversationProfile(self, *, conversationOwnerKey: str) -> ConversationProfileSnapshot:
        return ConversationProfileSnapshot(
            conversationOwnerKey=conversationOwnerKey,
            displayName=None,
            metadata={},
        )

    def upsertConversationProfile(self, **kwargs):
        del kwargs

    def deleteMessageTurns(self, **kwargs):
        del kwargs
        return 0


def test_post_messages_history_sem_persistencia_retorna_lista_vazia():
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages/history",
        json={"userId": "usuario-hist-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"turns": []}


def test_post_messages_history_convidado_retorna_turnos():
    fixed_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    rows = [
        UserMessageRecord(
            userRequest="olá",
            modelAnswer="oi",
            createdAt=fixed_time,
            turnId="turn-uuid-1",
            traceId="trace-1",
        )
    ]
    persistence = _HistoryPersistenceStub(rows)
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
        userMessagePersistence=persistence,
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages/history",
        json={"userId": "usuario-hist-2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert persistence.lastOwnerKey == "guest:usuario-hist-2"
    assert len(body["turns"]) == 1
    assert body["turns"][0]["userRequest"] == "olá"
    assert body["turns"][0]["modelAnswer"] == "oi"
    assert body["turns"][0]["turnId"] == "turn-uuid-1"
    assert body["turns"][0]["traceId"] == "trace-1"


class _ContractGoogleVerifier:
    def verifyIdToken(self, idToken: str) -> GoogleIdentity:
        if idToken != "valid-contract-google":
            raise InvalidGoogleTokenError("bad")
        return GoogleIdentity(
            subject="sub-contract-xyz",
            email="c@example.com",
            issuer="https://accounts.google.com",
            audience="aud",
        )


def test_post_messages_history_google_escopo_correto():
    persistence = _HistoryPersistenceStub([])
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
        googleTokenVerifier=_ContractGoogleVerifier(),
        userMessagePersistence=persistence,
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages/history",
        json={"userId": "x", "googleIdToken": "valid-contract-google"},
    )
    assert response.status_code == 200
    assert persistence.lastOwnerKey == "google:sub-contract-xyz"


def test_post_messages_history_google_token_invalido_401():
    persistence = _HistoryPersistenceStub([])
    use_case = MessageUseCase(
        knowledgeAgent=_EchoKnowledge(),
        supportAgent=_EchoSupport(),
        swarmKnowledgeAgent=_EchoSwarm(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=_FixedRouteRouter("knowledge"),
        googleTokenVerifier=_ContractGoogleVerifier(),
        userMessagePersistence=persistence,
    )
    client = _make_client(use_case)
    response = client.post(
        "/messages/history",
        json={"userId": "x", "googleIdToken": "nope"},
    )
    assert response.status_code == 401
