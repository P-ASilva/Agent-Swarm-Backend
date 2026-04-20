import importlib
import os
from typing import Any, Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _resolve_factory_candidates() -> list[str]:
    env_candidate = os.getenv("TEST_APP_FACTORY", "").strip()
    candidates = [
        env_candidate,
        "app.main:create_app",
        "src.app.main:create_app",
        "api.main:create_app",
        "main:create_app",
        "app.main:app",
        "src.app.main:app",
        "api.main:app",
        "main:app",
    ]
    return [candidate for candidate in candidates if candidate]


def _import_factory_or_app(factory_ref: str) -> Callable[[], FastAPI]:
    module_name, attr_name = factory_ref.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    attr = getattr(module, attr_name)

    if callable(attr):
        return attr

    if isinstance(attr, FastAPI):
        return lambda: attr

    raise TypeError(
        f"Resolved '{factory_ref}' but attribute is neither callable nor FastAPI."
    )


@pytest.fixture(scope="session")
def app_factory() -> Callable[[], FastAPI]:
    failures: list[str] = []
    for candidate in _resolve_factory_candidates():
        try:
            return _import_factory_or_app(candidate)
        except Exception as exc:  # pragma: no cover - this is for test bootstrap diagnostics
            failures.append(f"{candidate}: {exc!r}")

    failure_text = "\n".join(f"- {item}" for item in failures) if failures else "- none"
    pytest.fail(
        "Could not resolve FastAPI app factory.\n"
        "Set TEST_APP_FACTORY to '<module>:<create_app_or_app>' or implement one of:\n"
        "- app.main:create_app\n"
        "- src.app.main:create_app\n"
        "- api.main:create_app\n"
        "- main:create_app\n"
        "Tried candidates:\n"
        f"{failure_text}"
    )


@pytest.fixture
def app(app_factory: Callable[[], FastAPI]) -> FastAPI:
    return app_factory()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def message_payload() -> dict[str, str]:
    return {
        "message": "How can I use my phone as a card machine?",
        "user_id": "client789",
    }


@pytest.fixture
def dependency_overrider(app: FastAPI):
    applied: list[Any] = []

    def _apply(original_dep: Callable[..., Any], override_dep: Callable[..., Any]) -> None:
        app.dependency_overrides[original_dep] = override_dep
        applied.append(original_dep)

    yield _apply

    for dep in applied:
        app.dependency_overrides.pop(dep, None)
