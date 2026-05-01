from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.domain.errors import PersistencyUnavailableError
from app.domain.ports import InvalidGoogleTokenError
from app.main import createApp


def test_post_messages_401_token_google_invalido():
    class _BadGoogle:
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise InvalidGoogleTokenError("token inválido")

    client = TestClient(createApp(messageUseCase=_BadGoogle()))
    response = client.post(
        "/messages",
        json={"message": "Olá", "userId": "u", "googleIdToken": "x"},
    )
    assert response.status_code == 401
    assert "inválido" in response.json()["detail"].lower() or "expirado" in response.json()["detail"].lower()


def test_post_messages_503_runtime_error():
    class _Boom:
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("indisponível")

    client = TestClient(createApp(messageUseCase=_Boom()))
    response = client.post(
        "/messages",
        json={"message": "Olá", "userId": "u"},
    )
    assert response.status_code == 503


def test_post_messages_504_timeout():
    class _Slow:
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise TimeoutError

    client = TestClient(createApp(messageUseCase=_Slow()))
    response = client.post(
        "/messages",
        json={"message": "Olá", "userId": "u"},
    )
    assert response.status_code == 504


def test_post_messages_503_persistencia_propaga_detalhe():
    class _PersistDown:
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise PersistencyUnavailableError("Banco de sessão indisponível para teste.")

    client = TestClient(createApp(messageUseCase=_PersistDown()))
    response = client.post(
        "/messages",
        json={"message": "Olá", "userId": "u"},
    )
    assert response.status_code == 503
    assert "indisponível" in response.json()["detail"].lower()
