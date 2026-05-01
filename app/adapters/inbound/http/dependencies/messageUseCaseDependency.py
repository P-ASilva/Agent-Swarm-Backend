from __future__ import annotations

import os

from fastapi import Request

from app.adapters.outbound.google import GoogleTokenVerifierAdapter
from app.adapters.outbound.guardrails import RuleBasedGuardrailsAdapter
from app.adapters.outbound.openai import OpenAiChatAdapter, OpenAiWebSearchAdapter
from app.adapters.outbound.postgres import (
    KnowledgeIngestionToolAdapter,
    PgvectorKnowledgeRetriever,
    UserMessagePersistenceAdapter,
)
from app.application.agents import KnowledgeAgent, RouterAgent, SupportAgent, SwarmKnowledgeAgent
from app.application.support_operations_executor import SupportOperationsExecutor
from app.application.usecase import MessageUseCase
from app.domain.ports import MessageGuardrailsPort, MessageUseCasePort
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
    persistence = UserMessagePersistenceAdapter.fromEnv()
    supportModel = os.getenv("SUPPORT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    supportOpsExecutor = SupportOperationsExecutor(userMessagePersistence=persistence)
    supportAgent = SupportAgent(
        openAiChat=openAiChat,
        executor=supportOpsExecutor,
        supportModel=supportModel,
    )
    swarmGuideLabel = os.getenv("SWARM_KNOWLEDGE_LABEL", "implementation-guide").strip() or "implementation-guide"
    messageGuardrails = _buildMessageGuardrailsFromEnv()
    knowledgeAgent = KnowledgeAgent(
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
    )
    useCase = MessageUseCase(
        knowledgeAgent=knowledgeAgent,
        supportAgent=supportAgent,
        swarmKnowledgeAgent=SwarmKnowledgeAgent(),
        messageGuardrails=messageGuardrails,
        routerModel=RouterAgent(openAiChat=openAiChat),
        knowledgeModelLabel=knowledgeModel,
        supportModelLabel=supportModel,
        swarmKnowledgeLabel=swarmGuideLabel,
        googleTokenVerifier=googleVerifier,
        userMessagePersistence=persistence,
    )
    request.app.state._messageUseCase = useCase
    return useCase


def _buildMessageGuardrailsFromEnv() -> MessageGuardrailsPort:
    mode = os.getenv("GUARDRAILS_MODE", "").strip().lower()
    if mode != "rules":
        return RuleBasedGuardrailsAdapter()
    inputRaw = os.getenv("GUARDRAILS_INPUT_BLOCK_SUBSTRINGS", "")
    outputRaw = os.getenv("GUARDRAILS_OUTPUT_BLOCK_SUBSTRINGS", "")
    maxRaw = os.getenv("GUARDRAILS_MAX_INPUT_CHARS", "0").strip() or "0"
    try:
        maxChars = max(0, int(maxRaw))
    except ValueError:
        maxChars = 0
    inputSubs = tuple(s.strip().casefold() for s in inputRaw.split(",") if s.strip())
    outputSubs = tuple(s.strip().casefold() for s in outputRaw.split(",") if s.strip())
    return RuleBasedGuardrailsAdapter(
        inputBlockedSubstrings=inputSubs,
        outputBlockedSubstrings=outputSubs,
        maxInputChars=maxChars,
    )


def _buildGoogleVerifierOptional() -> GoogleTokenVerifierAdapter | None:
    if not os.getenv("GOOGLE_CLIENT_ID", "").strip():
        return None
    return GoogleTokenVerifierAdapter.fromEnv()
