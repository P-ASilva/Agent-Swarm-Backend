from __future__ import annotations

from typing import Protocol

from app.domain.models import WebSearchResult


class WebSearchPort(Protocol):
    def search(self, query: str, *, maxResults: int = 5) -> list[WebSearchResult]:
        ...
