Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

Write-Host "=== KnowledgeAgent smoke: starting pgvector service ==="
docker compose up -d postgres

$script = @'
from fastapi.testclient import TestClient

from app.adapters.outbound.postgres import KnowledgeIngestionToolAdapter, PgvectorKnowledgeRetriever
from app.application.agents import KnowledgeAgent, SupportAgentMock
from app.application.usecase import DefaultMessageUseCase
from app.domain.models import RouterDecision
from app.main import createApp
from app.rag_pipeline import DeterministicEmbeddingProvider, WebContentLoader
from app.rag_pipeline.service import RagIngestionService
from app.rag_pipeline.store import PgvectorStore


class ForcedKnowledgeRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route="knowledge", rationale="forced-knowledge")


store = PgvectorStore()
embedding = DeterministicEmbeddingProvider(embeddingDim=1536)
service = RagIngestionService(store=store, embeddingProvider=embedding, loader=WebContentLoader())
store.applyMigrations()

knowledge_agent = KnowledgeAgent(
    retriever=PgvectorKnowledgeRetriever(embeddingProvider=embedding, store=store),
    ingestionTool=KnowledgeIngestionToolAdapter(ingestionService=service),
)
app = createApp(
    messageUseCase=DefaultMessageUseCase(
        routerModel=ForcedKnowledgeRouter(),
        knowledgeAgent=knowledge_agent,
        supportAgent=SupportAgentMock(),
    )
)
client = TestClient(app)

fixture_url = "https://www.infinitepay.io/pix"

add_response = client.post(
    "/messages",
    json={"message": f"Please add {fixture_url} to knowledge context", "userId": "client789"},
)
assert add_response.status_code == 200, add_response.text
assert "Knowledge context updated successfully." in add_response.json()["reply"], add_response.json()

answer_response = client.post(
    "/messages",
    json={"message": "How can I use my phone as a card machine?", "userId": "client789"},
)
assert answer_response.status_code == 200, answer_response.text
assert "Knowledge answer (grounded):" in answer_response.json()["reply"], answer_response.json()

print("KnowledgeAgent smoke checks passed.")
'@

$script | docker compose --profile rag run --build --rm rag_ingest python -
