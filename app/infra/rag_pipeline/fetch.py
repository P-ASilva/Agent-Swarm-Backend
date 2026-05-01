from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from app.infra.rag_pipeline.normalize import canonicalizeUrl, extractTitleAndText


@dataclass(frozen=True)
class FetchedDocument:
    sourceUrl: str
    canonicalUrl: str
    title: str | None
    text: str
    metadata: dict[str, str]


_DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class WebContentLoader:
    timeoutSeconds: float = 20.0
    maxRetries: int = 2
    userAgent: str = _DEFAULT_BROWSER_UA

    def load(self, sourceUrl: str) -> FetchedDocument:
        parsed = urlparse(sourceUrl)
        if parsed.scheme == "file":
            return self._loadFromFile(sourceUrl)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme for ingestion: {sourceUrl}")

        headers = {
            "User-Agent": self.userAgent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        lastError: Exception | None = None
        for _ in range(self.maxRetries + 1):
            try:
                response = httpx.get(
                    sourceUrl,
                    headers=headers,
                    follow_redirects=True,
                    timeout=self.timeoutSeconds,
                )
                response.raise_for_status()
                title, text = extractTitleAndText(response.text)
                return FetchedDocument(
                    sourceUrl=sourceUrl,
                    canonicalUrl=canonicalizeUrl(str(response.url)),
                    title=title,
                    text=text,
                    metadata={
                        "content_type": response.headers.get("content-type", "unknown"),
                        "status_code": str(response.status_code),
                    },
                )
            except Exception as exc:  # pragma: no cover - retries make deterministic coverage hard
                lastError = exc

        assert lastError is not None
        reason = f"{type(lastError).__name__}: {lastError}"
        raise RuntimeError(f"Failed to fetch source URL: {sourceUrl} ({reason})") from lastError

    def loadMany(self, sourceUrls: list[str], maxPages: int | None = None) -> list[FetchedDocument]:
        capped = sourceUrls[:maxPages] if maxPages is not None else sourceUrls
        return [self.load(sourceUrl) for sourceUrl in capped]

    def _loadFromFile(self, sourceUrl: str) -> FetchedDocument:
        parsed = urlparse(sourceUrl)
        rawPath = unquote(parsed.path)
        normalizedPath = rawPath
        if rawPath.startswith("/") and len(rawPath) > 2 and rawPath[2] == ":":
            # Handle file:///C:/... style paths on Windows hosts.
            normalizedPath = rawPath[1:]
        filePath = Path(normalizedPath)
        if not filePath.exists():
            raise FileNotFoundError(f"Local file URL not found: {sourceUrl}")
        html = filePath.read_text(encoding="utf-8")
        title, text = extractTitleAndText(html)
        return FetchedDocument(
            sourceUrl=sourceUrl,
            canonicalUrl=canonicalizeUrl(sourceUrl),
            title=title,
            text=text,
            metadata={"content_type": "text/html", "status_code": "200"},
        )
