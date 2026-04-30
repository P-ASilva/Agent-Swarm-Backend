from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievedChunk:
    chunkId: str
    text: str
    sourceUrl: str
    title: str | None
    score: float
    documentVersion: str
    metadata: dict[str, Any] = field(default_factory=dict)
