import importlib
import os
from dataclasses import dataclass, field
from typing import Any

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


def _setStateAttrIfExists(app: FastAPI, fakeUseCase: FakeMessageUseCase) -> bool:
    state = getattr(app, "state", None)
    if state is None:
        return False

    attrCandidates = ["messageUseCase", "chatUseCase"]
    for attr in attrCandidates:
        if hasattr(state, attr):
            setattr(state, attr, fakeUseCase)
            return True

    return False


def _applyDependencyOverrideIfConfigured(
    app: FastAPI, fakeUseCase: FakeMessageUseCase
) -> bool:
    depRef = os.getenv("TEST_USE_CASE_DEP", "").strip()
    if not depRef:
        return False

    moduleName, attrName = depRef.split(":", maxsplit=1)
    module = importlib.import_module(moduleName)
    originalDep = getattr(module, attrName)
    app.dependency_overrides[originalDep] = lambda: fakeUseCase
    return True


def installMessageUseCaseOverride(app: FastAPI, fakeUseCase: FakeMessageUseCase) -> None:
    if _setStateAttrIfExists(app, fakeUseCase):
        return

    if _applyDependencyOverrideIfConfigured(app, fakeUseCase):
        return

    raise AssertionError(
        "Could not inject fake message use case.\n"
        "Supported options:\n"
        "- Keep use case on app.state.<messageUseCase|chatUseCase>\n"
        "- Or set TEST_USE_CASE_DEP to '<module>:<dependency_provider>' for dependency overrides."
    )
