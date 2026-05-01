from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RouteName = Literal["knowledge", "support"]


@dataclass(frozen=True)
class RouterDecision:
    route: RouteName
    rationale: str = ""
    usedModel: str | None = None
    degraded: bool = False
    reply: str | None = None
