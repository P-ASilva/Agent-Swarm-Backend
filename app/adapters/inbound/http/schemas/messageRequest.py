from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="User message to be processed by the agent swarm.",
        examples=["How can I use my phone as a card machine?"],
    )
    userId: str = Field(
        min_length=1,
        description="Stable identifier for the user context.",
        examples=["client789"],
    )
