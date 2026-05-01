from __future__ import annotations

import os

from fastapi import Request

from app.adapters.outbound.google import GoogleTokenVerifierAdapter
from app.adapters.outbound.openai import OpenAiChatAdapter, OpenAiWebSearchAdapter
from app.adapters.outbound.postgres import (
    KnowledgeIngestionToolAdapter,
    PgvectorKnowledgeRetriever,
    UserMessagePersistenceAdapter,
)
from app.application.agents import KnowledgeAgent, RouterAgent, SupportAgentMock
from app.application.usecase import MessageUseCase
from app.domain.ports import MessageUseCasePort
from app.infra.rag_pipeline import WebContentLoader, buildEmbeddingProviderFromEnv
from app.infra.rag_pipeline.service import RagIngestionService
from app.infra.rag_pipeline.store import PgvectorStore


def getMessageUseCase(request: Request) -> MessageUseCasePort:
    configured = getattr(request.app.state, "messageUseCase", None)
    if configured is not None:
        return configured

    cached = getattr(request.app.state, "_messageUseCase", None)
    if cached is not None:
        return cached

    openAiChat = OpenAiChatAdapter.fromEnv()
    knowledgeModel = os.getenv("KNOWLEDGE_MODEL", "gpt-4.1-mini").strip()
    embeddingProvider = buildEmbeddingProviderFromEnv()
    ragStore = PgvectorStore()
    ragIngestionService = RagIngestionService(
        store=ragStore,
        embeddingProvider=embeddingProvider,
        loader=WebContentLoader(),
    )
    googleVerifier = _buildGoogleVerifierOptional()
    webSearch = OpenAiWebSearchAdapter.fromEnv()
    useCase = MessageUseCase(
        routerModel=RouterAgent(openAiChat=openAiChat),
        knowledgeAgent=KnowledgeAgent(
            retriever=PgvectorKnowledgeRetriever(
                embeddingProvider=embeddingProvider,
                store=ragStore,
            ),
            ingestionTool=KnowledgeIngestionToolAdapter(
                ingestionService=ragIngestionService,
            ),
            openAiChat=openAiChat,
            webSearch=webSearch,
            responseModel=knowledgeModel,
        ),
        supportAgent=SupportAgentMock(openAiChat=openAiChat),
        googleTokenVerifier=googleVerifier,
        userMessagePersistence=UserMessagePersistenceAdapter.fromEnv(),
    )
    request.app.state._messageUseCase = useCase
    return useCase


def _buildGoogleVerifierOptional() -> GoogleTokenVerifierAdapter | None:
    if not os.getenv("GOOGLE_CLIENT_ID", "").strip():
        return None
    return GoogleTokenVerifierAdapter.fromEnv()
