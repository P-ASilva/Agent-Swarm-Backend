from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailVerdict:
    allowed: bool
    reply: str | None = None
    rewrittenMessage: str | None = None
    degraded: bool = False
    auditCode: str = "allowed"
