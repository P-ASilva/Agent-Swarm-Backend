from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeIngestionResult:
    runId: str
    status: str
    documentsProcessed: int
    chunksWritten: int
    seedUrlCount: int
