from __future__ import annotations

from fastapi import Request

from app.adapters.outbound.openai import OpenAiChatAdapter, OpenAiRouterModelPlugin
from app.application.agents import FallbackAgentMock, KnowledgeAgentMock, SupportAgentMock
from app.application.usecase import DefaultMessageUseCase
from app.domain.ports import MessageUseCasePort


def getMessageUseCase(request: Request) -> MessageUseCasePort:
    configured = getattr(request.app.state, "messageUseCase", None)
    if configured is not None:
        return configured

    cached = getattr(request.app.state, "_defaultMessageUseCase", None)
    if cached is not None:
        return cached

    openAiChat = OpenAiChatAdapter.fromEnv()
    routerModel = OpenAiRouterModelPlugin(openAiChat=openAiChat)
    useCase = DefaultMessageUseCase(
        routerModel=routerModel,
        knowledgeAgent=KnowledgeAgentMock(openAiChat=openAiChat),
        supportAgent=SupportAgentMock(openAiChat=openAiChat),
        fallbackAgent=FallbackAgentMock(openAiChat=openAiChat),
    )
    request.app.state._defaultMessageUseCase = useCase
    return useCase
