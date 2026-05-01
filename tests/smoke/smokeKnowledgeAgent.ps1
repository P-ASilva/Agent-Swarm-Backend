Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

Write-Host "=== KnowledgeAgent smoke: starting pgvector service ==="
docker compose up -d postgres

$script = @'
from fastapi.testclient import TestClient

from app.adapters.outbound.postgres import KnowledgeIngestionToolAdapter, PgvectorKnowledgeRetriever
from app.application.agents import KnowledgeAgent
from app.application.usecase import MessageUseCase
from app.domain.models import RouterDecision
from app.main import createApp
from app.infra.rag_pipeline import DeterministicEmbeddingProvider, WebContentLoader
from app.infra.rag_pipeline.service import RagIngestionService
from app.infra.rag_pipeline.store import PgvectorStore


class ForcedKnowledgeRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route="knowledge", rationale="forced-knowledge")


class UnusedRouteAgent:
    def handleMessage(self, message: str) -> str:
        raise AssertionError("support/swarm should not run in knowledge smoke")


store = PgvectorStore()
embedding = DeterministicEmbeddingProvider(embeddingDim=1536)
service = RagIngestionService(store=store, embeddingProvider=embedding, loader=WebContentLoader())
store.applyMigrations()

knowledge_agent = KnowledgeAgent(
    retriever=PgvectorKnowledgeRetriever(embeddingProvider=embedding, store=store),
    ingestionTool=KnowledgeIngestionToolAdapter(ingestionService=service),
)
app = createApp(
    messageUseCase=MessageUseCase(
        knowledgeAgent=knowledge_agent,
        supportAgent=UnusedRouteAgent(),
        swarmKnowledgeAgent=UnusedRouteAgent(),
        routerModel=ForcedKnowledgeRouter(),
    )
)
client = TestClient(app)

fixture_url = "https://www.infinitepay.io/pix"

add_response = client.post(
    "/messages",
    json={"message": f"Por favor adicione {fixture_url} ao contexto de conhecimento", "userId": "client789"},
)
assert add_response.status_code == 200, add_response.text
assert "Contexto de conhecimento atualizado com sucesso." in add_response.json()["reply"], add_response.json()

answer_response = client.post(
    "/messages",
    json={"message": "Como usar o celular como maquininha de cartão?", "userId": "client789"},
)
assert answer_response.status_code == 200, answer_response.text
assert "[fontes:" in answer_response.json()["reply"], answer_response.json()

print("Smoke do Agente de Conhecimento concluído com sucesso.")
'@

$script | docker compose --profile rag run --build --rm rag_ingest python -
