from pydantic import BaseModel, Field


class MessageResponseEnvelope(BaseModel):
    status: str = Field(description="Result state for the message processing flow.")
    reply: str = Field(description="End-user-safe response text.")
    traceId: str = Field(description="Correlation identifier for tracing requests.")
    route: str | None = Field(
        default=None,
        description="Dispatch route persisted for the turn: knowledge, support, or swarm.",
    )
    routerModel: str | None = Field(
        default=None,
        description="Model id used by the router LLM when routing ran.",
    )
    agentModel: str | None = Field(
        default=None,
        description="Model id used by the answering agent when an agent produced the reply.",
    )
    replySource: str | None = Field(
        default=None,
        description="Origin of the reply: guardrail, router, knowledge, support, or swarm.",
    )
