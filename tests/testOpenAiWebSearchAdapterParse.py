from __future__ import annotations

import json

from app.adapters.outbound.openai.openAiWebSearchAdapter import parseOpenAiResponsesWebSearchBody
from app.application.agents.knowledgeAgent import KnowledgeAgent
from app.domain.models import RetrievedChunk, WebSearchResult


def test_parseOpenAiResponsesExtractsCitationSlices():
    body = {
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Hello world.",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://bcb.gov.br",
                                "title": "BCB",
                                "start_index": 0,
                                "end_index": 5,
                            }
                        ],
                    }
                ],
            },
        ]
    }
    results = parseOpenAiResponsesWebSearchBody(body)
    assert len(results) == 1
    assert results[0].content == "Hello"
    assert results[0].url == "https://bcb.gov.br"
    assert results[0].title == "BCB"
    assert results[0].score == 1.0


def test_parseOpenAiResponsesNoAnnotationsUsesFullText():
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "  Full synthetic answer.  ", "annotations": []},
                ],
            },
        ]
    }
    results = parseOpenAiResponsesWebSearchBody(body)
    assert len(results) == 1
    assert results[0].content == "Full synthetic answer."
    assert results[0].url == ""


def test_parseOpenAiResponsesMalformedReturnsEmpty():
    assert parseOpenAiResponsesWebSearchBody({}) == []
    assert parseOpenAiResponsesWebSearchBody({"output": None}) == []


class _FixedWebSearch:
    def __init__(self, results: list[WebSearchResult]) -> None:
        self._results = results

    def search(self, query: str, *, maxResults: int = 5):
        del query
        return self._results[:maxResults]


class _CountingWebSearch(_FixedWebSearch):
    def __init__(self, results: list[WebSearchResult]) -> None:
        super().__init__(results)
        self.callCount = 0

    def search(self, query: str, *, maxResults: int = 5):
        self.callCount += 1
        return super().search(query, maxResults=maxResults)


class _TwoShotChatAdapter:
    def __init__(self) -> None:
        self.invocationCount = 0

    def chatCompletion(
        self,
        *,
        messages,
        model,
        temperature=0.0,
        responseFormat=None,
    ):
        del messages, model, temperature, responseFormat
        self.invocationCount += 1
        if self.invocationCount == 1:
            return json.dumps(
                {"answer": "Desculpe, não disponho sobre Selic nos trechos fornecidos."}
            )
        return json.dumps({"answer": "Selic em 10,5% conforme os trechos da busca na web citados."})


class _LowScoreRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5):
        del query, topK
        return [
            RetrievedChunk(
                chunkId="low",
                text="weak rag",
                sourceUrl="https://example.invalid/rag",
                title=None,
                score=0.1,
                documentVersion="v1",
            )
        ]


class _StrongRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5):
        del query, topK
        return [
            RetrievedChunk(
                chunkId="hi",
                text="strong rag snippet",
                sourceUrl="https://infinitepay.io/pix",
                title="Pix",
                score=0.92,
                documentVersion="v1",
            )
        ]


class _MediumSimilarityRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5):
        del query, topK
        return [
            RetrievedChunk(
                chunkId="mid",
                text="Tap to pay onboarding text",
                sourceUrl="https://www.infinitepay.io/tap-to-pay",
                title="Tap",
                score=0.58,
                documentVersion="v1",
            )
        ]


class _EmptyRetriever:
    def retrieveRelevant(self, *, query: str, topK: int = 5):
        del query, topK
        return []


class _NoopIngestion:
    def addUrl(self, *, url: str, crawlVersion: str | None = None, runLabel: str | None = None):
        raise AssertionError(url, crawlVersion, runLabel)


def test_knowledgeAgentPrefersWebWhenRagWeakAndWebSearchConfigured():
    agent = KnowledgeAgent(
        retriever=_LowScoreRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=_FixedWebSearch(
            [WebSearchResult(content="from the web", url="https://src.test", title="Src", score=1.0)]
        ),
    )
    reply = agent.handleMessage("some question")
    assert "from the web" in reply


def test_knowledgeAgentSkipsWebWhenRagStrongEvenIfWebSearchConfigured():
    agent = KnowledgeAgent(
        retriever=_StrongRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=_FixedWebSearch(
            [WebSearchResult(content="from the web", url="https://src.test", title="Src", score=1.0)]
        ),
    )
    reply = agent.handleMessage("some question")
    assert "strong rag snippet" in reply
    assert "from the web" not in reply


def test_knowledgeAgentDedicatedWebSearchBypassesStrongRagWhenUserAsks():
    agent = KnowledgeAgent(
        retriever=_StrongRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=_FixedWebSearch(
            [WebSearchResult(content="resultado da web dedicada", url="https://web.only", title="W", score=1.0)]
        ),
    )
    reply = agent.handleMessage("Pesquise na web sobre taxa Selic atual")
    assert "resultado da web dedicada" in reply
    assert "strong rag snippet" not in reply


def test_knowledgeAgentDedicatedWebFallsBackToRagWhenWebReturnsEmpty():
    agent = KnowledgeAgent(
        retriever=_StrongRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=_FixedWebSearch([]),
    )
    reply = agent.handleMessage("Busca na internet: algo que não vai retornar")
    assert "strong rag snippet" in reply


def test_knowledgeAgentEmptyRagAndEmptyWebReturnsPromptForUrl():
    agent = KnowledgeAgent(
        retriever=_EmptyRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=_FixedWebSearch([]),
    )
    reply = agent.handleMessage("some question")
    assert "Ainda não encontrei contexto fundamentado" in reply


def test_knowledgeAgentNoWebSearchUsesWeakRagChunk():
    agent = KnowledgeAgent(
        retriever=_LowScoreRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=None,
    )
    reply = agent.handleMessage("some question")
    assert "weak rag" in reply


def test_knowledgeAgentUsesWebWhenSimilarityBelowConfiguredFloor():
    web = _FixedWebSearch(
        [WebSearchResult(content="external rate context", url="https://bcb.gov.br", title="BCB", score=1.0)]
    )
    agent = KnowledgeAgent(
        retriever=_MediumSimilarityRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=None,
        webSearch=web,
    )
    reply = agent.handleMessage("Qual a taxa Selic?")
    assert "external rate context" in reply
    assert "tap-to-pay" not in reply.lower()


def test_knowledgeAgentRetriesWebWhenFormatterAdmitsInsufficientContext():
    web = _CountingWebSearch(
        [
            WebSearchResult(
                content="Copom definiu Selic em 10,50% ao ano.",
                url="https://bcb.gov.br",
                title="BCB",
                score=1.0,
            )
        ]
    )
    chat = _TwoShotChatAdapter()
    agent = KnowledgeAgent(
        retriever=_StrongRetriever(),
        ingestionTool=_NoopIngestion(),
        openAiChat=chat,
        webSearch=web,
        responseModel="stub-model",
    )
    reply = agent.handleMessage("Qual a Selic hoje?")
    assert "10,5" in reply or "10,50" in reply
    assert web.callCount == 1
    assert chat.invocationCount == 2
