from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.domain.models import GoogleIdentity
from app.domain.ports import GoogleTokenVerifierPort, InvalidGoogleTokenError

ALLOWED_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def _defaultGoogleClientId() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


@dataclass
class GoogleTokenVerifierAdapter(GoogleTokenVerifierPort):
    clientId: str
    tokenInfoUrl: str = "https://oauth2.googleapis.com/tokeninfo"
    timeoutSeconds: float = 8.0

    @classmethod
    def fromEnv(cls) -> "GoogleTokenVerifierAdapter":
        clientId = _defaultGoogleClientId()
        if not clientId:
            raise RuntimeError("GOOGLE_CLIENT_ID is not configured.")
        return cls(clientId=clientId)

    def verifyIdToken(self, idToken: str) -> GoogleIdentity:
        token = idToken.strip()
        if not token:
            raise InvalidGoogleTokenError("Google ID token is required.")

        response = httpx.get(
            self.tokenInfoUrl,
            params={"id_token": token},
            timeout=self.timeoutSeconds,
        )
        if response.status_code != 200:
            raise InvalidGoogleTokenError("Google token verification failed.")

        payload = response.json()
        audience = str(payload.get("aud", "")).strip()
        issuer = str(payload.get("iss", "")).strip()
        subject = str(payload.get("sub", "")).strip()
        emailRaw = payload.get("email")
        email = str(emailRaw).strip() if isinstance(emailRaw, str) and emailRaw.strip() else None

        if audience != self.clientId:
            raise InvalidGoogleTokenError("Google token audience mismatch.")
        if issuer not in ALLOWED_ISSUERS:
            raise InvalidGoogleTokenError("Google token issuer is invalid.")
        if not subject:
            raise InvalidGoogleTokenError("Google token subject is missing.")

        expRaw = str(payload.get("exp", "")).strip()
        if not expRaw.isdigit():
            raise InvalidGoogleTokenError("Google token expiration claim is invalid.")
        expiresAt = datetime.fromtimestamp(int(expRaw), tz=UTC)
        if expiresAt <= datetime.now(UTC):
            raise InvalidGoogleTokenError("Google token has expired.")

        return GoogleIdentity(
            subject=subject,
            email=email,
            issuer=issuer,
            audience=audience,
        )
