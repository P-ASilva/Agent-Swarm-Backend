from __future__ import annotations

from pydantic import BaseModel, Field


class MessageHistoryRequest(BaseModel):
    userId: str = Field(
        min_length=1,
        description="Same client-stable label as POST /messages (guest bucket or client_user_label).",
    )
    googleIdToken: str | None = Field(
        default=None,
        description="When set and valid, history is scoped to google:<subject> instead of guest:<userId>.",
    )
