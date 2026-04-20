from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from app.application.use_cases import DefaultMessageUseCase, MessageUseCase
from app.schemas import HealthResponse, MessageRequest, MessageResponseEnvelope


def get_message_use_case(app: FastAPI) -> MessageUseCase:
    return app.state.message_use_case


def create_app(message_use_case: MessageUseCase | None = None) -> FastAPI:
    app = FastAPI(
        title="Agent Swarm API",
        version="0.1.0",
        description="Inbound API adapters for message orchestration and health checks.",
    )
    app.state.message_use_case = message_use_case or DefaultMessageUseCase()

    @app.post(
        "/messages",
        response_model=MessageResponseEnvelope,
        summary="Process a user message",
        response_description="Normalized message response envelope.",
        responses={
            422: {"description": "Request payload validation failed."},
            503: {"description": "A required downstream dependency is unavailable."},
            504: {"description": "A downstream dependency timed out."},
        },
        tags=["messages"],
    )
    async def post_messages(
        payload: MessageRequest,
        use_case: MessageUseCase = Depends(lambda: get_message_use_case(app)),
    ) -> MessageResponseEnvelope:
        payload_dict = payload.model_dump()
        try:
            raw_result: dict[str, Any] = await use_case.execute(payload_dict)
        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="Timed out while processing message dependencies.",
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail="Message dependency is currently unavailable.",
            ) from exc

        return MessageResponseEnvelope.model_validate(raw_result)

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Health probe",
        response_description="Service health status.",
        tags=["health"],
    )
    async def get_health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()

