from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.agents.knowledgeIntent import KnowledgeIntent
from app.domain.conversationContextMarkers import FULL_CURRENT_USER_MESSAGE_LEADER
from app.domain.models import RetrievedChunk, WebSearchResult
from app.domain.ports import AgentHandlerPort, KnowledgeIngestionToolPort, KnowledgeRetrieverPort
from app.domain.ports import OpenAiChatPort, WebSearchPort
from app.modeling.prompts.knowledge import (
    KNOWLEDGE_OUTPUT_CONTRACT,
    KNOWLEDGE_SYSTEM_PROMPT,
    KNOWLEDGE_WEB_CONTEXT_ADDENDUM,
)

RAG_SCORE_FLOOR_WHEN_WEB_CONFIGURED = 0.62

_ENVELOPE_INSUFFICIENCY_MARKERS = (
    "não disponho",
    "não tenho informações",
    "informação insuficiente",
    "informações insuficientes",
    "contexto insuficiente",
    "não foi possível localizar",
    "não encontrei",
    "não consta nos conteúdos",
    "não constam nos conteúdos",
    "sem informações nos trechos",
    "cannot find grounded",
    "insufficient context",
)

URL_PATTERN = re.compile(r"(https?://[^\s]+|file://[^\s]+)", re.IGNORECASE)
ADD_URL_HINTS = ("add", "ingest", "index", "adicione", "adicionar", "ingerir", "indexar")

_DEDICATED_WEB_SEARCH_INTENT = re.compile(
    r"|".join(
        [
            r"fora\s+do\s+contexto",
            r"fora\s+da\s+base",
            r"fora\s+do\s+material",
            r"n[aã]o\s+(?:est[áa]|consta|vejo)\s+no\s+contexto",
            r"n[aã]o\s+consta\s+na\s+base",
            r"n[aã]o\s+tenho\s+isso\s+nos\s+trechos",
            r"informa[cç][aã]o(?:s)?\s+fora\s+do\s+contexto",
            r"informa[cç][aã]o\s+externa",
            r"pesquis\w*\s+na\s+(?:web|internet)",
            r"busc\w*\s+na\s+(?:web|internet)",
            r"procur\w*\s+na\s+internet",
            r"procur\w*\s+online",
            r"outside\s+(?:of\s+)?(?:the\s+)?context",
            r"search\s+(?:the\s+)?web",
            r"look\s+this\s+up\s+online",
        ]
    ),
    re.IGNORECASE,
)

_WEB_SEARCH_QUERY_PREFIX = re.compile(
    r"^\s*(?:por\s+favor\s+)?(?:"
    r"pesquis\w*\s+na\s+(?:web|internet)\s*(?:sobre|por)?\s*[:]?\s*|"
    r"busc\w*\s+na\s+(?:web|internet)\s*(?:sobre|por)?\s*[:]?\s*|"
    r"procur\w*\s+na\s+internet\s*(?:sobre|por)?\s*[:]?\s*"
    r")\s*",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeAgent(AgentHandlerPort):
    retriever: KnowledgeRetrieverPort
    ingestionTool: KnowledgeIngestionToolPort
    retrievalTopK: int = 3
    openAiChat: OpenAiChatPort | None = None
    webSearch: WebSearchPort | None = None
    ragRelevanceThreshold: float = 0.45
    responseModel: str = "gpt-4.1-mini"

    def handleMessage(self, message: str) -> str:
        intent = self._parseIntent(message)
        logger.info("intent kind=%s url=%s", intent.kind, intent.url or "-")
        if intent.kind == "add_url" and intent.url:
            try:
                result = self.ingestionTool.addUrl(
                    url=intent.url,
                    crawlVersion=datetime.now(UTC).strftime("%Y%m%d"),
                    runLabel="knowledge-agent-add-url",
                )
            except Exception as exc:
                detail = str(exc).strip()
                if len(detail) > 200:
                    detail = f"{detail[:197]}..."
                logger.warning(
                    "addUrl failed url=%s type=%s",
                    intent.url,
                    type(exc).__name__,
                    exc_info=True,
                )
                suffix = f" {detail}" if detail else ""
                return (
                    "Falha ao atualizar o contexto de conhecimento. "
                    f"[url={intent.url} erro={type(exc).__name__}{suffix}]"
                )
            return (
                "Contexto de conhecimento atualizado com sucesso. "
                f"[url={intent.url} execução={result.runId} trechos={result.chunksWritten}]"
            )

        bareForFlow = self._extractBareMessage(message)
        if (
            intent.kind == "answer"
            and self.webSearch is not None
            and self._messageRequestsDedicatedWebSearch(bareForFlow)
        ):
            query = self._queryTextForDedicatedWebSearch(bareForFlow)
            logger.info("dedicated web search path queryLen=%d", len(query))
            try:
                webFirst = self.webSearch.search(query, maxResults=5)
            except Exception:
                webFirst = []
            if webFirst:
                synthetic = self._webResultsAsChunks(webFirst)
                return self._answerFromRagChunks(
                    message=message,
                    chunks=synthetic,
                    sourceLabel="web_search",
                    contextIntro="Resultados de busca na web (citados)",
                    webBackedContext=True,
                )
            logger.info("dedicated web search returned no results — falling back to RAG")

        logger.info("retrieval topK=%d", self.retrievalTopK)
        try:
            chunks = self.retriever.retrieveRelevant(query=message, topK=self.retrievalTopK)
        except Exception as exc:
            return (
                "A recuperação de conhecimento está temporariamente indisponível. "
                f"[erro={type(exc).__name__}]"
            )

        useWebGate = self.webSearch is not None
        strongThresh = self._effectiveRagStrengthThreshold()
        ragStrong = bool(chunks) and chunks[0].score >= strongThresh

        if useWebGate and not ragStrong:
            webResults: list[WebSearchResult] = []
            if self.webSearch:
                try:
                    if chunks:
                        logger.info("rag score below threshold — falling back to web search")
                    else:
                        logger.info("rag retrieval miss — falling back to web search")
                    webResults = self.webSearch.search(
                        self._extractBareMessage(message), maxResults=5
                    )
                except Exception:
                    webResults = []

            if webResults:
                synthetic = self._webResultsAsChunks(webResults)
                return self._answerFromRagChunks(
                    message=message,
                    chunks=synthetic,
                    sourceLabel="web_search",
                    contextIntro="Resultados de busca na web (citados)",
                    webBackedContext=True,
                )

            if not chunks:
                return (
                    "Ainda não encontrei contexto fundamentado na base de conhecimento. "
                    "Informe uma URL de fonte para que eu possa adicioná-la ao contexto."
                )

            return self._answerFromRagChunks(
                message=message, chunks=chunks, webBackedContext=False
            )

        if not useWebGate:
            if not chunks:
                return (
                    "Ainda não encontrei contexto fundamentado na base de conhecimento. "
                    "Informe uma URL de fonte para que eu possa adicioná-la ao contexto."
                )
            return self._answerFromRagChunks(
                message=message, chunks=chunks, webBackedContext=False
            )

        reply = self._answerFromRagChunks(
            message=message, chunks=chunks, webBackedContext=False
        )
        if (
            self.openAiChat
            and self._groundedEnvelopeAdmitsInsufficientContext(reply)
        ):
            logger.info(
                "formatter signaled missing factual context despite strong retrieval — retrying via web search"
            )
            try:
                webRetry = (
                    self.webSearch.search(self._extractBareMessage(message), maxResults=5)
                    if self.webSearch
                    else []
                )
            except Exception:
                webRetry = []
            if webRetry:
                synthetic = self._webResultsAsChunks(webRetry)
                return self._answerFromRagChunks(
                    message=message,
                    chunks=synthetic,
                    sourceLabel="web_search",
                    contextIntro="Resultados de busca na web (citados)",
                    webBackedContext=True,
                )

        return reply

    def _webResultsAsChunks(self, results: list[WebSearchResult]) -> list[RetrievedChunk]:
        out: list[RetrievedChunk] = []
        for index, row in enumerate(results):
            out.append(
                RetrievedChunk(
                    chunkId=f"web:{index}",
                    text=row.content,
                    sourceUrl=row.url,
                    title=row.title,
                    score=float(row.score),
                    documentVersion="web_search",
                    metadata={"source": "web_search"},
                )
            )
        return out

    def _effectiveRagStrengthThreshold(self) -> float:
        if self.webSearch is None:
            return self.ragRelevanceThreshold
        return max(self.ragRelevanceThreshold, RAG_SCORE_FLOOR_WHEN_WEB_CONFIGURED)

    def _groundedEnvelopeAdmitsInsufficientContext(self, envelope: str) -> bool:
        lower = envelope.lower()
        return any(marker in lower for marker in _ENVELOPE_INSUFFICIENCY_MARKERS)

    def _sourcesSuffixFromChunks(self, chunks: list[RetrievedChunk], *, limit: int = 2) -> str:
        labels: list[str] = []
        for chunk in chunks:
            raw = (chunk.sourceUrl or "").strip()
            if not raw or raw == "-":
                continue
            if raw not in labels:
                labels.append(raw)
            if len(labels) >= limit:
                break
        if not labels:
            return ""
        return f" [fontes: {', '.join(labels)}]"

    def _answerFromRagChunks(
        self,
        *,
        message: str,
        chunks: list[RetrievedChunk],
        sourceLabel: str = "rag",
        contextIntro: str = "Contexto recuperado (RAG)",
        webBackedContext: bool = False,
    ) -> str:
        if not chunks:
            return (
                "Ainda não encontrei contexto fundamentado na base de conhecimento. "
                "Informe uma URL de fonte para que eu possa adicioná-la ao contexto."
            )

        logger.info(
            "generating grounded answer model=%s chunks=%d source=%s",
            self.responseModel,
            len(chunks),
            sourceLabel,
        )
        if self.openAiChat:
            try:
                answer = self._buildGroundedAnswerWithModel(
                    message=message,
                    chunks=chunks,
                    contextIntro=contextIntro,
                    webBackedContext=webBackedContext,
                )
                return f"{answer}{self._sourcesSuffixFromChunks(chunks)}"
            except Exception:
                pass

        primary = chunks[0]
        return f"{primary.text}{self._sourcesSuffixFromChunks(chunks)}"

    def _buildGroundedAnswerWithModel(
        self,
        *,
        message: str,
        chunks: list[RetrievedChunk],
        contextIntro: str = "Contexto recuperado (RAG)",
        webBackedContext: bool = False,
    ) -> str:
        if not self.openAiChat:
            raise RuntimeError("knowledge formatting model is not configured")

        contextLines = []
        for index, chunk in enumerate(chunks, start=1):
            snippet = chunk.text.strip().replace("\n", " ")
            if len(snippet) > 700:
                snippet = snippet[:700].rstrip() + "..."
            contextLines.append(
                f"[{index}] source={chunk.sourceUrl} title={chunk.title or '-'} score={chunk.score:.4f}\n"
                f"{snippet}"
            )
        contextBlock = "\n\n".join(contextLines)
        userPrompt = (
            "Pergunta do usuário:\n"
            f"{message}\n\n"
            f"{contextIntro}:\n"
            f"{contextBlock}"
        )

        completionMessages: list[dict[str, str]] = [
            {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
        ]
        if webBackedContext:
            completionMessages.append(
                {"role": "system", "content": KNOWLEDGE_WEB_CONTEXT_ADDENDUM},
            )
        completionMessages.append(
            {"role": "system", "content": KNOWLEDGE_OUTPUT_CONTRACT},
        )
        completionMessages.append({"role": "user", "content": userPrompt})

        content = self.openAiChat.chatCompletion(
            messages=completionMessages,
            model=self.responseModel,
            temperature=0.1,
            responseFormat={"type": "json_object"},
        )
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise RuntimeError("invalid-knowledge-answer-payload")
        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("knowledge-answer-missing")
        return answer.strip()

    def _extractBareMessage(self, message: str) -> str:
        idx = message.rfind(FULL_CURRENT_USER_MESSAGE_LEADER)
        if idx != -1:
            return message[idx + len(FULL_CURRENT_USER_MESSAGE_LEADER) :].strip()
        legacy = "Current user message:\n"
        idxLegacy = message.rfind(legacy)
        if idxLegacy != -1:
            return message[idxLegacy + len(legacy) :].strip()
        return message

    def _messageRequestsDedicatedWebSearch(self, bareMessage: str) -> bool:
        return bool(_DEDICATED_WEB_SEARCH_INTENT.search(bareMessage.strip()))

    def _queryTextForDedicatedWebSearch(self, bareMessage: str) -> str:
        stripped = _WEB_SEARCH_QUERY_PREFIX.sub("", bareMessage.strip()).strip()
        return stripped if stripped else bareMessage.strip()

    def _parseIntent(self, message: str) -> KnowledgeIntent:
        parsed = self._parseStructuredIntent(message)
        if parsed is not None:
            return parsed

        bareMessage = self._extractBareMessage(message)
        lower = bareMessage.lower()
        urlMatch = URL_PATTERN.search(bareMessage)
        if urlMatch:
            urlStart = urlMatch.start()
            textBeforeUrl = lower[:urlStart]
            if any(hint in textBeforeUrl for hint in ADD_URL_HINTS):
                return KnowledgeIntent(kind="add_url", url=urlMatch.group(1))

        return KnowledgeIntent(kind="answer")

    def _parseStructuredIntent(self, message: str) -> KnowledgeIntent | None:
        text = message.strip()
        if not text.startswith("{") or not text.endswith("}"):
            return None

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        tool = str(payload.get("tool", payload.get("action", ""))).strip().lower()
        url = payload.get("url")
        if tool in {"add-url", "add_url", "add-url-to-context", "add_url_to_context"} and isinstance(url, str):
            cleaned = url.strip()
            if cleaned:
                return KnowledgeIntent(kind="add_url", url=cleaned)
        return None
