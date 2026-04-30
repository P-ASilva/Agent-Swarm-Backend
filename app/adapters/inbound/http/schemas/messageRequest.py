from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="User message to be processed by the agent swarm.",
        examples=["How can I use my phone as a card machine?"],
    )
    userId: str = Field(
        min_length=1,
        description=(
            "Client-stable label used to bucket guest turns (guest:userId persistence key); "
            "also forwarded as client_user_label in storage."
        ),
        examples=["client789"],
    )
    googleIdToken: str | None = Field(
        default=None,
        description=(
            "Optional Google ID token. When valid, same-day persisted history keyed to the Google "
            "subject is loaded and turns are linked to app_users via upsert."
        ),
    )
