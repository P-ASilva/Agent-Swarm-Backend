import importlib
import os
from typing import Any, Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _resolveFactoryCandidates() -> list[str]:
    envCandidate = os.getenv("TEST_APP_FACTORY", "").strip()
    candidates = [
        envCandidate,
        "app.main:createApp",
        "src.app.main:createApp",
        "api.main:createApp",
        "main:createApp",
        "app.main:app",
        "src.app.main:app",
        "api.main:app",
        "main:app",
    ]
    return [candidate for candidate in candidates if candidate]


def _importFactoryOrApp(factoryRef: str) -> Callable[[], FastAPI]:
    moduleName, attrName = factoryRef.split(":", maxsplit=1)
    module = importlib.import_module(moduleName)
    attr = getattr(module, attrName)

    if callable(attr):
        return attr

    if isinstance(attr, FastAPI):
        return lambda: attr

    raise TypeError(
        f"Resolved '{factoryRef}' but attribute is neither callable nor FastAPI."
    )


@pytest.fixture(scope="session")
def appFactory() -> Callable[[], FastAPI]:
    failures: list[str] = []
    for candidate in _resolveFactoryCandidates():
        try:
            return _importFactoryOrApp(candidate)
        except Exception as exc:  # pragma: no cover - this is for test bootstrap diagnostics
            failures.append(f"{candidate}: {exc!r}")

    failureText = "\n".join(f"- {item}" for item in failures) if failures else "- none"
    pytest.fail(
        "Could not resolve FastAPI app factory.\n"
        "Set TEST_APP_FACTORY to '<module>:<createApp_or_app>' or implement one of:\n"
        "- app.main:createApp\n"
        "- src.app.main:createApp\n"
        "- api.main:createApp\n"
        "- main:createApp\n"
        "Tried candidates:\n"
        f"{failureText}"
    )


@pytest.fixture
def app(appFactory: Callable[[], FastAPI]) -> FastAPI:
    return appFactory()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def messagePayload() -> dict[str, str]:
    return {
        "message": "How can I use my phone as a card machine?",
        "userId": "client789",
    }


@pytest.fixture
def dependencyOverrider(app: FastAPI):
    applied: list[Any] = []

    def _apply(originalDep: Callable[..., Any], overrideDep: Callable[..., Any]) -> None:
        app.dependency_overrides[originalDep] = overrideDep
        applied.append(originalDep)

    yield _apply

    for dep in applied:
        app.dependency_overrides.pop(dep, None)
