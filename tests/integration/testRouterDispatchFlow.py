from app.application.agents import KnowledgeAgent, SupportAgentMock
from app.application.usecase import DefaultMessageUseCase
from app.domain.models import KnowledgeIngestionResult, RetrievedChunk, RouterDecision


class StubKnowledgeRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route="knowledge", rationale="forced-knowledge")


class StubRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5) -> list[RetrievedChunk]:
        del topK
        return [
            RetrievedChunk(
                chunkId="chunk-1",
                text=f"Grounded context for: {query}",
                sourceUrl="https://www.infinitepay.io",
                title="Infinitepay",
                score=0.9,
                documentVersion="20260429",
            )
        ]


class StubIngestionTool:
    def addUrl(
        self,
        *,
        url: str,
        crawlVersion: str | None = None,
        runLabel: str | None = None,
    ) -> KnowledgeIngestionResult:
        del crawlVersion, runLabel
        return KnowledgeIngestionResult(
            runId="run-knowledge",
            status="completed",
            documentsProcessed=1,
            chunksWritten=2,
            seedUrlCount=1,
        )


def testDefaultRouterPathReturnsFallbackAgentReply(client, monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "")

    response = client.post(
        "/messages",
        json={"message": "What should I do here?", "userId": "client789"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reply"].startswith("Fallback agent answered:")


def testRouterKnowledgePathReturnsKnowledgeAgentGroundedReply(app, client):
    app.state.messageUseCase = DefaultMessageUseCase(
        routerModel=StubKnowledgeRouter(),
        knowledgeAgent=KnowledgeAgent(
            retriever=StubRetriever(),
            ingestionTool=StubIngestionTool(),
        ),
        supportAgent=SupportAgentMock(),
    )

    response = client.post(
        "/messages",
        json={"message": "What are Infinitepay services?", "userId": "client789"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Knowledge answer (grounded):" in body["reply"]
