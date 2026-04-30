from __future__ import annotations

from typing import Protocol

from app.domain.models import GoogleIdentity


class InvalidGoogleTokenError(RuntimeError):
    """Raised when a Google ID token is invalid or expired."""


class GoogleTokenVerifierPort(Protocol):
    def verifyIdToken(self, idToken: str) -> GoogleIdentity:
        """Validate and decode a Google ID token."""
