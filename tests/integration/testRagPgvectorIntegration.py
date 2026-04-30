from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.infra.rag_pipeline.chunk import DeterministicChunker
from app.infra.rag_pipeline.embed import DeterministicEmbeddingProvider
from app.infra.rag_pipeline.fetch import FetchedDocument
from app.infra.rag_pipeline.sources import computeSeedManifestHash
from app.infra.rag_pipeline.store import PgvectorStore


@pytest.mark.integration
def testRagStoreUpsertAndRetrievalFlow():
    databaseUrl = os.getenv("RAG_TEST_DATABASE_URL", "").strip()
    if not databaseUrl:
        pytest.skip("Set RAG_TEST_DATABASE_URL to run pgvector integration test.")

    crawlVersion = f"test-{uuid4().hex[:8]}"
    store = PgvectorStore(databaseUrl=databaseUrl, schemaVersion="v1")
    store.applyMigrations()

    runId = store.startIngestionRun(
        runLabel="pytest-rag",
        runType="ingest",
        seedManifestHash=computeSeedManifestHash(["https://www.infinitepay.io/pix"]),
        contextPath="tests",
    )

    document = FetchedDocument(
        sourceUrl="https://www.infinitepay.io/pix",
        canonicalUrl="https://www.infinitepay.io/pix",
        title="Infinitepay Pix",
        text="Receive instant Pix payments with transparent rates and simple onboarding.",
        metadata={"source": "pytest"},
    )
    chunker = DeterministicChunker(chunkSize=80, overlap=20)
    chunks = chunker.chunkText(document.text)
    embeddingsProvider = DeterministicEmbeddingProvider(embeddingDim=1536)
    embeddings = embeddingsProvider.embedTexts([chunk.text for chunk in chunks])

    _, inserted = store.upsertDocumentAndChunks(
        document=document,
        chunks=chunks,
        embeddings=embeddings,
        crawlVersion=crawlVersion,
        embeddingModel=embeddingsProvider.modelName,
        embeddingDim=embeddingsProvider.embeddingDim,
        runId=runId,
    )
    assert inserted == len(chunks)

    queryEmbedding = embeddingsProvider.embedTexts(["instant pix payments"])[0]
    rows = store.querySimilarChunks(
        queryEmbedding=queryEmbedding,
        topK=3,
        embeddingModel=embeddingsProvider.modelName,
    )
    assert rows
    assert rows[0]["source_url"] == "https://www.infinitepay.io/pix"

    store.finishIngestionRun(
        runId=runId,
        status="completed",
        stats={"documents_processed": 1, "chunks_written": inserted},
    )
