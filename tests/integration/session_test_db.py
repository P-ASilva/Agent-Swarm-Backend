from __future__ import annotations

import os

_DEFAULT_LOCAL_SESSION_DB = "postgresql://session_swarm:session_swarm@localhost:5433/session_swarm"
_CONNECT_TIMEOUT_SECONDS = 3


def _withConnectTimeout(url: str, seconds: int = _CONNECT_TIMEOUT_SECONDS) -> str:
    if not url or "connect_timeout=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}connect_timeout={seconds}"


def resolve_session_integration_database_url() -> str:
    explicit = os.getenv("SESSION_TEST_DATABASE_URL", "").strip()
    if explicit:
        return _withConnectTimeout(explicit)
    session = os.getenv("SESSION_DATABASE_URL", "").strip()
    if session:
        return _withConnectTimeout(session)
    return _withConnectTimeout(_DEFAULT_LOCAL_SESSION_DB)
