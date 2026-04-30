from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.postgres import KnowledgeIngestionToolAdapter
from app.application.agents import KnowledgeAgent, SupportAgentMock
from app.application.usecase import MessageUseCase
from app.domain.models import RouterDecision
from app.main import createApp
from app.infra.rag_pipeline import DeterministicEmbeddingProvider, WebContentLoader
from app.infra.rag_pipeline.service import RagIngestionService
from app.infra.rag_pipeline.store import PgvectorStore


class StubKnowledgeRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route="knowledge", rationale="forced-knowledge")


class EmptyRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5):
        del query, topK
        return []


@pytest.mark.integration
def testKnowledgeAgentAddUrlUpdatesRagDatabase():
    databaseUrl = os.getenv("RAG_TEST_DATABASE_URL", "").strip()
    if not databaseUrl:
        pytest.skip("Set RAG_TEST_DATABASE_URL to run database mutation integration tests.")

    fixtureUrl = Path("tests/fixtures/rag/infinitepay_tap_to_pay.html").resolve().as_uri()

    store = PgvectorStore(databaseUrl=databaseUrl, schemaVersion="v1")
    ingestionService = RagIngestionService(
        store=store,
        embeddingProvider=DeterministicEmbeddingProvider(embeddingDim=1536),
        loader=WebContentLoader(),
    )
    try:
        ingestionService.store.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping DB mutation integration test due unavailable test DB: {exc}")

    useCase = MessageUseCase(
        routerModel=StubKnowledgeRouter(),
        knowledgeAgent=KnowledgeAgent(
            retriever=EmptyRetriever(),
            ingestionTool=KnowledgeIngestionToolAdapter(ingestionService=ingestionService),
        ),
        supportAgent=SupportAgentMock(),
    )
    app = createApp(messageUseCase=useCase)
    client = TestClient(app)

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM rag_source_documents")
            beforeDocs = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM rag_chunks")
            beforeChunks = int(cursor.fetchone()[0])

    response = client.post(
        "/messages",
        json={
            "message": f"Please add {fixtureUrl} to knowledge context",
            "userId": "client789",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Knowledge context updated successfully." in body["reply"]

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM rag_source_documents")
            afterDocs = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM rag_chunks")
            afterChunks = int(cursor.fetchone()[0])

    assert afterDocs >= beforeDocs + 1
    assert afterChunks >= beforeChunks + 1
