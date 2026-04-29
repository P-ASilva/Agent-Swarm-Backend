from pydantic import BaseModel, Field


class MessageResponseEnvelope(BaseModel):
    status: str = Field(description="Result state for the message processing flow.")
    reply: str = Field(description="End-user-safe response text.")
    traceId: str = Field(description="Correlation identifier for tracing requests.")
