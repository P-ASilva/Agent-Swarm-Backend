from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.http.dependencies import getMessageUseCase
from app.adapters.inbound.http.schemas import (
    HealthResponse,
    MessageHistoryRequest,
    MessageHistoryResponse,
    MessageRequest,
    MessageResponseEnvelope,
)
from app.domain.errors import PersistencyUnavailableError
from app.domain.ports import InvalidGoogleTokenError, MessageUseCasePort


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
        401: {"description": "Google identity token is invalid or expired."},
        422: {"description": "Request payload validation failed."},
        503: {"description": "A required downstream dependency is unavailable."},
        504: {"description": "A downstream dependency timed out."},
    },
)
async def postMessages(
    payload: MessageRequest,
    useCase: MessageUseCasePort = Depends(getMessageUseCase),
) -> MessageResponseEnvelope:
    payloadDict = {
        "message": payload.message,
        "userId": payload.userId,
        "googleIdToken": payload.googleIdToken,
    }
    try:
        rawResult: dict[str, Any] = await useCase.execute(payloadDict)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token de login Google inválido ou expirado.",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="Tempo esgotado ao processar dependências da mensagem.",
        ) from exc
    except PersistencyUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dependência da mensagem está temporariamente indisponível.",
        ) from exc

    return MessageResponseEnvelope.model_validate(rawResult)


@apiRouter.post(
    "/messages/history",
    response_model=MessageHistoryResponse,
    tags=["messages"],
    summary="List today's persisted message turns",
    response_description="Chronological turns for the same owner key as POST /messages.",
    responses={
        401: {"description": "Google identity token is invalid or expired."},
        422: {"description": "Request payload validation failed."},
        503: {"description": "A required downstream dependency is unavailable."},
    },
)
async def postMessagesHistory(
    payload: MessageHistoryRequest,
    useCase: MessageUseCasePort = Depends(getMessageUseCase),
) -> MessageHistoryResponse:
    payloadDict = {
        "userId": payload.userId,
        "googleIdToken": payload.googleIdToken,
    }
    try:
        raw = await useCase.listTodayHistory(payloadDict)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token de login Google inválido ou expirado.",
        ) from exc
    except PersistencyUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return MessageHistoryResponse.model_validate(raw)
