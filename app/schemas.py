from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="User message to be processed by the agent swarm.",
        examples=["How can I use my phone as a card machine?"],
    )
    user_id: str = Field(
        min_length=1,
        description="Stable identifier for the user context.",
        examples=["client789"],
    )


class MessageResponseEnvelope(BaseModel):
    status: str = Field(description="Result state for the message processing flow.")
    reply: str = Field(description="End-user-safe response text.")
    trace_id: str = Field(description="Correlation identifier for tracing requests.")


class HealthResponse(BaseModel):
    status: str = Field(description="Current service health state.", examples=["ok"])

