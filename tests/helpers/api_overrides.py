import importlib
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import FastAPI


@dataclass
class FakeMessageUseCase:
    response: dict[str, Any]
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if self.error is not None:
            raise self.error
        return self.response

    async def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.execute(payload)


def _set_state_attr_if_exists(app: FastAPI, fake_use_case: FakeMessageUseCase) -> bool:
    state = getattr(app, "state", None)
    if state is None:
        return False

    attr_candidates = ["message_use_case", "chat_use_case", "router_use_case"]
    for attr in attr_candidates:
        if hasattr(state, attr):
            setattr(state, attr, fake_use_case)
            return True

    container = getattr(state, "container", None)
    if container is not None:
        for attr in attr_candidates:
            if hasattr(container, attr):
                setattr(container, attr, fake_use_case)
                return True

    return False


def _apply_dependency_override_if_configured(
    app: FastAPI, fake_use_case: FakeMessageUseCase
) -> bool:
    dep_ref = os.getenv("TEST_USE_CASE_DEP", "").strip()
    if not dep_ref:
        return False

    module_name, attr_name = dep_ref.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    original_dep = getattr(module, attr_name)
    app.dependency_overrides[original_dep] = lambda: fake_use_case
    return True


def install_message_use_case_override(app: FastAPI, fake_use_case: FakeMessageUseCase) -> None:
    if _set_state_attr_if_exists(app, fake_use_case):
        return

    if _apply_dependency_override_if_configured(app, fake_use_case):
        return

    raise AssertionError(
        "Could not inject fake message use case.\n"
        "Supported options:\n"
        "- Keep use case on app.state.<message_use_case|chat_use_case|router_use_case>\n"
        "- Keep it on app.state.container.<message_use_case|chat_use_case|router_use_case>\n"
        "- Or set TEST_USE_CASE_DEP to '<module>:<dependency_provider>' for dependency_overrides."
    )
