from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.models import KnowledgeIngestionResult
from app.infra.rag_pipeline.chunk import DeterministicChunker
from app.infra.rag_pipeline.embed import EmbeddingProvider, buildEmbeddingProviderFromEnv
from app.infra.rag_pipeline.fetch import WebContentLoader
from app.infra.rag_pipeline.sources import computeSeedManifestHash, loadSeedUrls
from app.infra.rag_pipeline.store import PgvectorStore


@dataclass
class RagIngestionService:
    store: PgvectorStore
    embeddingProvider: EmbeddingProvider
    loader: WebContentLoader

    @classmethod
    def fromEnv(cls) -> "RagIngestionService":
        return cls(
            store=PgvectorStore(),
            embeddingProvider=buildEmbeddingProviderFromEnv(),
            loader=WebContentLoader(),
        )

    def run(
        self,
        *,
        runType: str,
        contextPath: str | None = None,
        manifestPath: str | None = None,
        explicitUrls: list[str] | None = None,
        crawlVersion: str | None = None,
        maxPages: int | None = None,
        chunkSize: int = 1200,
        chunkOverlap: int = 150,
        runLabel: str | None = None,
        applyMigrations: bool = True,
    ) -> KnowledgeIngestionResult:
        seedUrls = loadSeedUrls(
            contextPath=contextPath,
            explicitUrls=explicitUrls,
            manifestPath=manifestPath,
        )
        seedManifestHash = computeSeedManifestHash(seedUrls)
        chunker = DeterministicChunker(chunkSize=chunkSize, overlap=chunkOverlap)
        effectiveCrawlVersion = crawlVersion or datetime.now(UTC).strftime("%Y%m%d")
        effectiveRunLabel = runLabel or f"{runType}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        if applyMigrations:
            self.store.applyMigrations()

        runId = self.store.startIngestionRun(
            runLabel=effectiveRunLabel,
            runType=runType,
            seedManifestHash=seedManifestHash,
            contextPath=manifestPath or ("direct-url-input" if explicitUrls else contextPath),
        )

        documentCount = 0
        chunkCount = 0
        try:
            documents = self.loader.loadMany(seedUrls, maxPages=maxPages)
            for document in documents:
                chunks = chunker.chunkText(document.text)
                if not chunks:
                    continue
                embeddings = self.embeddingProvider.embedTexts([chunk.text for chunk in chunks])
                _, inserted = self.store.upsertDocumentAndChunks(
                    document=document,
                    chunks=chunks,
                    embeddings=embeddings,
                    crawlVersion=effectiveCrawlVersion,
                    embeddingModel=self.embeddingProvider.modelName,
                    embeddingDim=self.embeddingProvider.embeddingDim,
                    runId=runId,
                )
                documentCount += 1
                chunkCount += inserted

            stats = {
                "documents_processed": documentCount,
                "chunks_written": chunkCount,
                "embedding_model": self.embeddingProvider.modelName,
                "embedding_dim": self.embeddingProvider.embeddingDim,
                "seed_url_count": len(seedUrls),
            }
            self.store.finishIngestionRun(runId=runId, status="completed", stats=stats)
            return KnowledgeIngestionResult(
                runId=runId,
                status="completed",
                documentsProcessed=documentCount,
                chunksWritten=chunkCount,
                seedUrlCount=len(seedUrls),
            )
        except Exception as exc:
            self.store.finishIngestionRun(
                runId=runId,
                status="failed",
                stats={"error": f"{type(exc).__name__}: {exc}"},
            )
            raise

    def addUrl(
        self,
        *,
        url: str,
        crawlVersion: str | None = None,
        runLabel: str | None = None,
        applyMigrations: bool = True,
    ) -> KnowledgeIngestionResult:
        return self.run(
            runType="add-url",
            explicitUrls=[url],
            contextPath=None,
            manifestPath=None,
            crawlVersion=crawlVersion,
            runLabel=runLabel,
            applyMigrations=applyMigrations,
        )
