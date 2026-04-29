from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.http.dependencies import getMessageUseCase
from app.adapters.inbound.http.schemas import (
    HealthResponse,
    MessageRequest,
    MessageResponseEnvelope,
)
from app.domain.ports import MessageUseCasePort


apiRouter = APIRouter()


@apiRouter.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health probe",
    response_description="Service health status.",
)
async def getHealth() -> HealthResponse:
    return HealthResponse(status="ok")


@apiRouter.post(
    "/messages",
    response_model=MessageResponseEnvelope,
    tags=["messages"],
    summary="Process a user message",
    response_description="Normalized message response envelope.",
    responses={
        422: {"description": "Request payload validation failed."},
        503: {"description": "A required downstream dependency is unavailable."},
        504: {"description": "A downstream dependency timed out."},
    },
)
async def postMessages(
    payload: MessageRequest,
    useCase: MessageUseCasePort = Depends(getMessageUseCase),
) -> MessageResponseEnvelope:
    payloadDict = {"message": payload.message, "userId": payload.userId}
    try:
        rawResult: dict[str, Any] = await useCase.execute(payloadDict)
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

    return MessageResponseEnvelope.model_validate(rawResult)
