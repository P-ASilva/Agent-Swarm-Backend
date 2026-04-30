from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import KnowledgeIngestionResult
from app.domain.ports import KnowledgeIngestionToolPort
from app.infra.rag_pipeline.service import RagIngestionService


@dataclass
class KnowledgeIngestionToolAdapter(KnowledgeIngestionToolPort):
    ingestionService: RagIngestionService

    def addUrl(
        self,
        *,
        url: str,
        crawlVersion: str | None = None,
        runLabel: str | None = None,
    ) -> KnowledgeIngestionResult:
        return self.ingestionService.addUrl(
            url=url,
            crawlVersion=crawlVersion,
            runLabel=runLabel,
        )
