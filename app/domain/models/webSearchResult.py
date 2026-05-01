from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebSearchResult:
    content: str
    url: str
    title: str | None
    score: float
