from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.models import KnowledgeIngestionResult
from app.domain.ports import KnowledgeIngestionToolPort
from app.infra.rag_pipeline.service import RagIngestionService

logger = logging.getLogger(__name__)


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
        logger.info("ingestion addUrl url=%s", url)
        result = self.ingestionService.addUrl(
            url=url,
            crawlVersion=crawlVersion,
            runLabel=runLabel,
        )
        logger.info(
            "ingestion complete runId=%s chunks=%d",
            result.runId,
            result.chunksWritten,
        )
        return result
