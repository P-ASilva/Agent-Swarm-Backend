from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.models import RetrievedChunk
from app.domain.ports import KnowledgeRetrieverPort
from app.infra.rag_pipeline.embed import EmbeddingProvider
from app.infra.rag_pipeline.store import PgvectorStore

logger = logging.getLogger(__name__)


@dataclass
class PgvectorKnowledgeRetriever(KnowledgeRetrieverPort):
    embeddingProvider: EmbeddingProvider
    store: PgvectorStore

    def retrieveRelevant(self, *, query: str, topK: int = 5) -> list[RetrievedChunk]:
        logger.info("retrieval query topK=%d", topK)
        queryEmbedding = self.embeddingProvider.embedTexts([query])[0]
        rows = self.store.querySimilarChunks(
            queryEmbedding=queryEmbedding,
            topK=topK,
            embeddingModel=self.embeddingProvider.modelName,
        )
        chunks = [
            RetrievedChunk(
                chunkId=row["chunk_id"],
                text=row["text"],
                sourceUrl=row["source_url"],
                title=row.get("title"),
                score=float(row["score"]),
                documentVersion=row["document_version"],
                metadata={"chunk_index": row["chunk_index"]},
            )
            for row in rows
        ]
        topScore = chunks[0].score if chunks else 0.0
        logger.info("retrieved chunks=%d topScore=%.4f", len(chunks), topScore)
        return chunks
