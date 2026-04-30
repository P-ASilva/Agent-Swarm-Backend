from __future__ import annotations

import os

from fastapi import Request

from app.adapters.outbound.openai import OpenAiChatAdapter, OpenAiRouterModelPlugin
from app.adapters.outbound.postgres import (
    KnowledgeIngestionToolAdapter,
    PgvectorKnowledgeRetriever,
)
from app.application.agents import FallbackAgentMock, KnowledgeAgent, SupportAgentMock
from app.application.usecase import DefaultMessageUseCase
from app.domain.ports import MessageUseCasePort
from app.infra.rag_pipeline import WebContentLoader, buildEmbeddingProviderFromEnv
from app.infra.rag_pipeline.service import RagIngestionService
from app.infra.rag_pipeline.store import PgvectorStore


def getMessageUseCase(request: Request) -> MessageUseCasePort:
    configured = getattr(request.app.state, "messageUseCase", None)
    if configured is not None:
        return configured

    cached = getattr(request.app.state, "_defaultMessageUseCase", None)
    if cached is not None:
        return cached

    openAiChat = OpenAiChatAdapter.fromEnv()
    routerModel= os.getenv("ROUTER_MODEL", "gpt-4o-mini").strip()
    knowledgeModel = os.getenv("KNOWLEDGE_MODEL", "gpt-4.1-mini").strip()
    embeddingProvider = buildEmbeddingProviderFromEnv()
    ragStore = PgvectorStore()
    ragIngestionService = RagIngestionService(
        store=ragStore,
        embeddingProvider=embeddingProvider,
        loader=WebContentLoader(),
    )
    routerModel = OpenAiRouterModelPlugin(openAiChat=openAiChat)
    useCase = DefaultMessageUseCase(
        routerModel=routerModel,
        knowledgeAgent=KnowledgeAgent(
            retriever=PgvectorKnowledgeRetriever(
                embeddingProvider=embeddingProvider,
                store=ragStore,
            ),
            ingestionTool=KnowledgeIngestionToolAdapter(
                ingestionService=ragIngestionService,
            ),
            openAiChat=openAiChat,
            responseModel=knowledgeModel,
        ),
        supportAgent=SupportAgentMock(openAiChat=openAiChat),
        fallbackAgent=FallbackAgentMock(openAiChat=openAiChat),
    )
    request.app.state._defaultMessageUseCase = useCase
    return useCase
