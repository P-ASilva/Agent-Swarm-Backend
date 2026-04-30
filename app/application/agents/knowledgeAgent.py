from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.agents.knowledgeIntent import KnowledgeIntent
from app.domain.models import RetrievedChunk
from app.domain.ports import OpenAiChatPort
from app.domain.ports import AgentHandlerPort, KnowledgeIngestionToolPort, KnowledgeRetrieverPort
from app.modeling.prompts.knowledge import KNOWLEDGE_OUTPUT_CONTRACT, KNOWLEDGE_SYSTEM_PROMPT

URL_PATTERN = re.compile(r"(https?://[^\s]+|file://[^\s]+)", re.IGNORECASE)
ADD_URL_HINTS = ("add", "context", "knowledge", "ingest", "index", "save")


@dataclass
class KnowledgeAgent(AgentHandlerPort):
    retriever: KnowledgeRetrieverPort
    ingestionTool: KnowledgeIngestionToolPort
    retrievalTopK: int = 3
    openAiChat: OpenAiChatPort | None = None
    responseModel: str = "gpt-4.1-mini"

    def handleMessage(self, message: str) -> str:
        intent = self._parseIntent(message)
        if intent.kind == "add_url" and intent.url:
            try:
                result = self.ingestionTool.addUrl(
                    url=intent.url,
                    crawlVersion=datetime.now(UTC).strftime("%Y%m%d"),
                    runLabel="knowledge-agent-add-url",
                )
            except Exception as exc:
                return (
                    "Knowledge context update failed. "
                    f"[url={intent.url} error={type(exc).__name__}]"
                )
            return (
                "Knowledge context updated successfully. "
                f"[url={intent.url} run_id={result.runId} chunks={result.chunksWritten}]"
            )

        try:
            chunks = self.retriever.retrieveRelevant(query=message, topK=self.retrievalTopK)
        except Exception as exc:
            return (
                "Knowledge retrieval is temporarily unavailable. "
                f"[error={type(exc).__name__}]"
            )
        if not chunks:
            return (
                "I could not find grounded context in the knowledge base yet. "
                "Provide a source URL so I can add it to context."
            )

        if self.openAiChat:
            try:
                answer = self._buildGroundedAnswerWithModel(message=message, chunks=chunks)
                sources = ", ".join(dict.fromkeys(chunk.sourceUrl for chunk in chunks[:2]))
                return f"Knowledge answer (grounded): {answer} [sources: {sources}]"
            except Exception:
                # Fall back to deterministic chunk response if formatting model fails.
                pass

        primary = chunks[0]
        sources = ", ".join(dict.fromkeys(chunk.sourceUrl for chunk in chunks[:2]))
        return (
            f"Knowledge answer (grounded): {primary.text} "
            f"[sources: {sources}]"
        )

    def _buildGroundedAnswerWithModel(self, *, message: str, chunks: list[RetrievedChunk]) -> str:
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
            "Pergunta do usuario:\n"
            f"{message}\n\n"
            "Contexto recuperado (RAG):\n"
            f"{contextBlock}"
        )

        content = self.openAiChat.chatCompletion(
            messages=[
                {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
                {"role": "system", "content": KNOWLEDGE_OUTPUT_CONTRACT},
                {"role": "user", "content": userPrompt},
            ],
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

    def _parseIntent(self, message: str) -> KnowledgeIntent:
        parsed = self._parseStructuredIntent(message)
        if parsed is not None:
            return parsed

        lower = message.lower()
        urlMatch = URL_PATTERN.search(message)
        if urlMatch and any(hint in lower for hint in ADD_URL_HINTS):
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
