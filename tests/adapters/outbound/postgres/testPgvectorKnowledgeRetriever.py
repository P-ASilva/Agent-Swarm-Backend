from app.adapters.outbound.postgres import PgvectorKnowledgeRetriever


class StubEmbeddingProvider:
    modelName = "stub-model"

    def embedTexts(self, texts: list[str]) -> list[list[float]]:
        assert texts
        return [[0.1] * 3]


class StubStore:
    def querySimilarChunks(self, *, queryEmbedding, topK, embeddingModel):
        assert queryEmbedding
        assert topK == 2
        assert embeddingModel == "stub-model"
        return [
            {
                "chunk_id": "chunk-1",
                "text": "Tap to Pay on your phone.",
                "chunk_index": 0,
                "source_url": "https://www.infinitepay.io/tap-to-pay",
                "title": "Tap to Pay",
                "document_version": "20260429",
                "score": 0.91,
            }
        ]


def testPgvectorKnowledgeRetrieverMapsStoreRowsToDomainChunks():
    retriever = PgvectorKnowledgeRetriever(
        embeddingProvider=StubEmbeddingProvider(),
        store=StubStore(),
    )

    result = retriever.retrieveRelevant(query="tap to pay", topK=2)

    assert len(result) == 1
    assert result[0].chunkId == "chunk-1"
    assert result[0].sourceUrl == "https://www.infinitepay.io/tap-to-pay"
    assert result[0].metadata["chunk_index"] == 0
