from __future__ import annotations

from typing import Protocol

from app.domain.models import RetrievedChunk


class KnowledgeRetrieverPort(Protocol):
    def retrieveRelevant(self, *, query: str, topK: int = 5) -> list[RetrievedChunk]:
        """Return model-agnostic retrieved chunks for RAG generation."""
