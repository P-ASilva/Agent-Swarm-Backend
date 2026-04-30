from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


KnowledgeIntentKind = Literal["answer", "add_url"]


@dataclass(frozen=True)
class KnowledgeIntent:
    kind: KnowledgeIntentKind
    url: str | None = None
