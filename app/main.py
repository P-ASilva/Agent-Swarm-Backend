from __future__ import annotations

import logging

from fastapi import FastAPI

from app.adapters.inbound.http.routes import apiRouter
from app.domain.ports import MessageUseCasePort

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


def createApp(
    messageUseCase: MessageUseCasePort | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Agent Swarm API",
        version="0.1.0",
        description="Inbound API adapters for message orchestration and health checks.",
    )
    app.state.messageUseCase = messageUseCase
    app.include_router(apiRouter)
    return app


app = createApp()
