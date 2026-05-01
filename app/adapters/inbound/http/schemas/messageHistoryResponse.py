from __future__ import annotations

from pydantic import BaseModel, Field


class MessageHistoryTurn(BaseModel):
    turnId: str = Field(description="Persisted turn id (UUID string).")
    traceId: str = Field(description="Trace id for the turn.")
    userRequest: str
    modelAnswer: str
    createdAt: str = Field(description="ISO-8601 timestamp from persistence.")


class MessageHistoryResponse(BaseModel):
    turns: list[MessageHistoryTurn] = Field(default_factory=list)
