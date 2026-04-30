from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str | None = None
    issuer: str | None = None
    audience: str | None = None
