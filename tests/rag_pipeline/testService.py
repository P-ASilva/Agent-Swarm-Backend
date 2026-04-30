from app.rag_pipeline.chunk import TextChunk
from app.rag_pipeline.fetch import FetchedDocument
from app.rag_pipeline.service import RagIngestionService


class StubStore:
    def __init__(self):
        self.migrationsApplied = False
        self.started = False
        self.finished = False
        self.calls = []

    def applyMigrations(self):
        self.migrationsApplied = True

    def startIngestionRun(self, *, runLabel, runType, seedManifestHash, contextPath):
        self.started = True
        self.calls.append((runLabel, runType, seedManifestHash, contextPath))
        return "run-123"

    def finishIngestionRun(self, *, runId, status, stats):
        self.finished = True
        self.calls.append((runId, status, stats))

    def upsertDocumentAndChunks(
        self,
        *,
        document,
        chunks,
        embeddings,
        crawlVersion,
        embeddingModel,
        embeddingDim,
        runId,
    ):
        del crawlVersion, embeddingModel, embeddingDim, runId
        assert document
        assert len(chunks) == len(embeddings)
        return "doc-1", len(chunks)


class StubEmbeddingProvider:
    modelName = "stub-embedding"
    embeddingDim = 3

    def embedTexts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class StubLoader:
    def loadMany(self, sourceUrls, maxPages=None):
        del sourceUrls, maxPages
        return [
            FetchedDocument(
                sourceUrl="https://example.com",
                canonicalUrl="https://example.com",
                title="Example",
                text="hello world",
                metadata={},
            )
        ]


def testRagIngestionServiceRunsSharedIngestionFlow():
    service = RagIngestionService(
        store=StubStore(),
        embeddingProvider=StubEmbeddingProvider(),
        loader=StubLoader(),
    )
    result = service.run(
        runType="ingest",
        explicitUrls=["https://example.com"],
        applyMigrations=True,
        chunkSize=50,
        chunkOverlap=0,
    )

    assert result.status == "completed"
    assert result.documentsProcessed == 1
    assert result.chunksWritten >= 1


def testRagIngestionServiceAddUrlUsesSamePath():
    service = RagIngestionService(
        store=StubStore(),
        embeddingProvider=StubEmbeddingProvider(),
        loader=StubLoader(),
    )
    result = service.addUrl(url="https://example.com", applyMigrations=False)

    assert result.status == "completed"
    assert result.seedUrlCount == 1
