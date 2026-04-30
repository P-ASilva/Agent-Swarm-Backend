from __future__ import annotations

from typing import Protocol

from app.domain.models import KnowledgeIngestionResult


class KnowledgeIngestionToolPort(Protocol):
    def addUrl(
        self,
        *,
        url: str,
        crawlVersion: str | None = None,
        runLabel: str | None = None,
    ) -> KnowledgeIngestionResult:
        """Ingest a direct URL into the RAG knowledge store."""
