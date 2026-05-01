from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        del args, kwargs
        return False

from app.domain.models import WebSearchResult
from app.domain.ports import WebSearchPort

logger = logging.getLogger(__name__)

_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"


def parseOpenAiResponsesWebSearchBody(body: dict[str, Any]) -> list[WebSearchResult]:
    output = body.get("output")
    if not isinstance(output, list):
        return []

    fullText = ""
    annotations: list[dict[str, Any]] = []

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contentList = item.get("content")
        if not isinstance(contentList, list):
            continue
        for block in contentList:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "output_text":
                continue
            textVal = block.get("text")
            if isinstance(textVal, str):
                fullText = textVal
            ann = block.get("annotations")
            if isinstance(ann, list):
                annotations = [a for a in ann if isinstance(a, dict)]
            break
        if fullText or annotations:
            break

    if not fullText.strip():
        return []

    results: list[WebSearchResult] = []
    for ann in annotations:
        if ann.get("type") != "url_citation":
            continue
        url = ann.get("url")
        if not isinstance(url, str):
            url = ""
        titleVal = ann.get("title")
        title = titleVal if isinstance(titleVal, str) else None
        startIdx = ann.get("start_index")
        endIdx = ann.get("end_index")
        try:
            si = int(startIdx) if startIdx is not None else 0
            ei = int(endIdx) if endIdx is not None else 0
        except (TypeError, ValueError):
            continue
        if ei > len(fullText):
            ei = len(fullText)
        if si < 0:
            si = 0
        if ei < si:
            continue
        cited = fullText[si:ei].strip()
        if not cited:
            continue
        results.append(WebSearchResult(content=cited, url=url, title=title, score=1.0))

    if results:
        return results

    return [WebSearchResult(content=fullText.strip(), url="", title=None, score=1.0)]


@dataclass
class OpenAiWebSearchAdapter(WebSearchPort):
    apiKey: str
    model: str = "gpt-4o-mini"
    timeoutSeconds: float = 15.0

    @classmethod
    def fromEnv(cls) -> OpenAiWebSearchAdapter | None:
        load_dotenv()
        apiKey = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("WEB_SEARCH_MODEL", "gpt-4o-mini").strip()
        if not apiKey:
            return None
        return cls(apiKey=apiKey, model=model or "gpt-4o-mini")

    def search(self, query: str, *, maxResults: int = 5) -> list[WebSearchResult]:
        if not self.apiKey.strip():
            return []

        q = query.strip()
        if not q:
            return []

        logger.info("web search query=len=%s model=%s", len(q), self.model)

        payload: dict[str, Any] = {
            "model": self.model,
            "tools": [{"type": "web_search_preview"}],
            "input": q,
        }
        headers = {
            "Authorization": f"Bearer {self.apiKey}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                _RESPONSES_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=self.timeoutSeconds,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            logger.info("web search request failed error=%s", type(exc).__name__)
            return []

        if not isinstance(body, dict):
            return []

        parsed = parseOpenAiResponsesWebSearchBody(body)
        clipped = parsed[: max(0, maxResults)]
        logger.info("web search returned results=%s", len(clipped))
        return clipped
