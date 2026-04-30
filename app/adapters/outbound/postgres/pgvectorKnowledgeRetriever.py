from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import RetrievedChunk
from app.domain.ports import KnowledgeRetrieverPort
from app.rag_pipeline.embed import EmbeddingProvider
from app.rag_pipeline.store import PgvectorStore


@dataclass
class PgvectorKnowledgeRetriever(KnowledgeRetrieverPort):
    embeddingProvider: EmbeddingProvider
    store: PgvectorStore

    def retrieveRelevant(self, *, query: str, topK: int = 5) -> list[RetrievedChunk]:
        queryEmbedding = self.embeddingProvider.embedTexts([query])[0]
        rows = self.store.querySimilarChunks(
            queryEmbedding=queryEmbedding,
            topK=topK,
            embeddingModel=self.embeddingProvider.modelName,
        )
        return [
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
