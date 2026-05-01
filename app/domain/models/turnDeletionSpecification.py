from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TurnDeletionKind = Literal["all", "by_turn_ids", "by_trace_ids"]


@dataclass(frozen=True)
class TurnDeletionSpecification:
    kind: TurnDeletionKind
    turnIds: tuple[str, ...] = ()
    traceIds: tuple[str, ...] = ()
