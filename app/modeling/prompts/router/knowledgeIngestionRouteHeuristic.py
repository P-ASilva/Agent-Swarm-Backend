from __future__ import annotations

import json
import re

from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER

_URL = re.compile(r"(https?://[^\s]+|file://[^\s]+)", re.IGNORECASE)
_ADD_HINTS = ("add", "ingest", "index", "adicione", "adicionar", "ingerir", "indexar")


def _currentUserSlice(contextualMessage: str) -> str:
    if FULL_CURRENT_USER_MESSAGE_LEADER in contextualMessage:
        return contextualMessage.split(FULL_CURRENT_USER_MESSAGE_LEADER)[-1].strip()
    return contextualMessage.strip()


def heuristicShouldRouteKnowledgeIngestion(contextualMessage: str) -> bool:
    text = _currentUserSlice(contextualMessage)
    if not text:
        return False
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(payload, dict):
                tool = str(payload.get("tool", payload.get("action", ""))).strip().lower()
                if tool in {"add-url", "add_url", "add-url-to-context", "add_url_to_context"}:
                    url = payload.get("url")
                    return isinstance(url, str) and bool(url.strip())

    lower = stripped.casefold()
    match = _URL.search(stripped)
    if not match:
        return False
    before = lower[: match.start()]
    return any(hint in before for hint in _ADD_HINTS)
