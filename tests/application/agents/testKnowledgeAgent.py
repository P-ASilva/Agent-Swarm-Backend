from app.application.agents import KnowledgeAgent
from app.domain.models import KnowledgeIngestionResult, RetrievedChunk


class StubRetriever:
    def __init__(self, rows: list[RetrievedChunk]):
        self.rows = rows
        self.calls: list[tuple[str, int]] = []

    def retrieveRelevant(self, *, query: str, topK: int = 5) -> list[RetrievedChunk]:
        self.calls.append((query, topK))
        return self.rows


class StubIngestionTool:
    def __init__(self):
        self.calls: list[str] = []

    def addUrl(
        self,
        *,
        url: str,
        crawlVersion: str | None = None,
        runLabel: str | None = None,
    ) -> KnowledgeIngestionResult:
        del crawlVersion, runLabel
        self.calls.append(url)
        return KnowledgeIngestionResult(
            runId="run-1",
            status="completed",
            documentsProcessed=1,
            chunksWritten=4,
            seedUrlCount=1,
        )


class StubOpenAiChat:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict[str, object]] = []

    def chatCompletion(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.0,
        responseFormat: dict[str, object] | None = None,
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "responseFormat": responseFormat,
            }
        )
        return self.response


def testKnowledgeAgentAnswersUsingRetrievedChunks():
    retriever = StubRetriever(
        rows=[
            RetrievedChunk(
                chunkId="chunk-1",
                text="Tap to Pay allows using your phone as a card machine.",
                sourceUrl="https://www.infinitepay.io/tap-to-pay",
                title="Tap to Pay",
                score=0.9,
                documentVersion="20260429",
            )
        ]
    )
    ingestionTool = StubIngestionTool()
    agent = KnowledgeAgent(retriever=retriever, ingestionTool=ingestionTool)

    reply = agent.handleMessage("How can I use my phone as a card machine?")

    assert "Knowledge answer (grounded):" in reply
    assert "https://www.infinitepay.io/tap-to-pay" in reply
    assert retriever.calls
    assert ingestionTool.calls == []


def testKnowledgeAgentUsesDedicatedModelAndFormattingPrompt():
    retriever = StubRetriever(
        rows=[
            RetrievedChunk(
                chunkId="chunk-1",
                text="InfiniteTap turns a phone into card machine with NFC.",
                sourceUrl="https://www.infinitepay.io/maquininha-celular",
                title="Maquininha no celular",
                score=0.97,
                documentVersion="20260429",
            )
        ]
    )
    ingestionTool = StubIngestionTool()
    openAiChat = StubOpenAiChat(response='{"answer":"Use o InfiniteTap no celular com NFC."}')
    agent = KnowledgeAgent(
        retriever=retriever,
        ingestionTool=ingestionTool,
        openAiChat=openAiChat,
        responseModel="gpt-4.1-mini",
    )

    reply = agent.handleMessage("Como usar o celular como maquininha?")

    assert "Knowledge answer (grounded): Use o InfiniteTap no celular com NFC." in reply
    assert "https://www.infinitepay.io/maquininha-celular" in reply
    assert len(openAiChat.calls) == 1
    call = openAiChat.calls[0]
    assert call["model"] == "gpt-4.1-mini"
    assert call["responseFormat"] == {"type": "json_object"}
    messages = call["messages"]
    assert isinstance(messages, list) and len(messages) == 3
    assert "Return STRICT JSON" in messages[1]["content"]
    assert "Contexto recuperado (RAG):" in messages[2]["content"]
    assert ingestionTool.calls == []


def testKnowledgeAgentStructuredAddUrlTrigger():
    retriever = StubRetriever(rows=[])
    ingestionTool = StubIngestionTool()
    agent = KnowledgeAgent(retriever=retriever, ingestionTool=ingestionTool)

    reply = agent.handleMessage(
        '{"tool":"add_url_to_context","url":"https://docs.example.com/new"}'
    )

    assert "Knowledge context updated successfully." in reply
    assert ingestionTool.calls == ["https://docs.example.com/new"]


def testKnowledgeAgentNaturalLanguageAddUrlTrigger():
    retriever = StubRetriever(rows=[])
    ingestionTool = StubIngestionTool()
    agent = KnowledgeAgent(retriever=retriever, ingestionTool=ingestionTool)

    reply = agent.handleMessage(
        "Please add https://example.com/context-article to knowledge context."
    )

    assert "Knowledge context updated successfully." in reply
    assert ingestionTool.calls == ["https://example.com/context-article"]
