from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


SupportOperationKind = Literal["noop", "profile_patch", "delete_turns"]


@dataclass(frozen=True)
class SupportOperation:
    kind: SupportOperationKind
    payload: dict[str, Any]


@dataclass(frozen=True)
class SupportParsedOutput:
    assistantReply: str
    operations: tuple[SupportOperation, ...]
