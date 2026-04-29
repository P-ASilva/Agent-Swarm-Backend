from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup


def normalizeWhitespace(value: str) -> str:
    return " ".join(value.split())


def canonicalizeUrl(rawUrl: str) -> str:
    parsed = urlparse(rawUrl.strip())
    cleanPath = parsed.path.rstrip("/") or "/"
    canonical = parsed._replace(fragment="", query="", path=cleanPath)
    return urlunparse(canonical)


def extractTitleAndText(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    titleTag = soup.find("title")
    title = normalizeWhitespace(titleTag.get_text(" ", strip=True)) if titleTag else None
    text = normalizeWhitespace(soup.get_text(" ", strip=True))
    return title, text
