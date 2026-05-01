from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserMessageRecord:
    userRequest: str
    modelAnswer: str
    createdAt: datetime
    turnId: str | None = None
    traceId: str | None = None
