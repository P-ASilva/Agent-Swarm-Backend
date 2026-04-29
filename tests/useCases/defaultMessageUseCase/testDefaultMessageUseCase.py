import asyncio

from app.application.usecase import DefaultMessageUseCase
from app.domain.models import RouterDecision


class StubRouter:
    def __init__(self, route: str):
        self.route = route

    def decideRoute(self, message: str) -> RouterDecision:
        return RouterDecision(route=self.route, rationale="stub-router")


class StubAgent:
    def __init__(self, label: str):
        self.label = label
        self.messages: list[str] = []

    def handleMessage(self, message: str) -> str:
        self.messages.append(message)
        return f"{self.label} answered: {message}"


def testDefaultMessageUseCaseRoutesToKnowledgeAgent():
    knowledge = StubAgent("knowledge")
    support = StubAgent("support")
    fallback = StubAgent("fallback")
    useCase = DefaultMessageUseCase(
        routerModel=StubRouter(route="knowledge"),
        knowledgeAgent=knowledge,
        supportAgent=support,
        fallbackAgent=fallback,
    )

    result = asyncio.run(useCase.execute({"message": "hello", "userId": "client789"}))

    assert result["status"] == "ok"
    assert result["reply"] == "knowledge answered: hello"
    assert isinstance(result["traceId"], str)
    assert knowledge.messages == ["hello"]
    assert support.messages == []
    assert fallback.messages == []


def testDefaultMessageUseCaseRoutesToSupportAgent():
    knowledge = StubAgent("knowledge")
    support = StubAgent("support")
    fallback = StubAgent("fallback")
    useCase = DefaultMessageUseCase(
        routerModel=StubRouter(route="support"),
        knowledgeAgent=knowledge,
        supportAgent=support,
        fallbackAgent=fallback,
    )

    result = asyncio.run(useCase.execute({"message": "need help", "userId": "client789"}))

    assert result["status"] == "ok"
    assert result["reply"] == "support answered: need help"
    assert support.messages == ["need help"]
    assert knowledge.messages == []
    assert fallback.messages == []


def testDefaultMessageUseCaseRoutesToFallbackAgent():
    knowledge = StubAgent("knowledge")
    support = StubAgent("support")
    fallback = StubAgent("fallback")
    useCase = DefaultMessageUseCase(
        routerModel=StubRouter(route="fallback"),
        knowledgeAgent=knowledge,
        supportAgent=support,
        fallbackAgent=fallback,
    )

    result = asyncio.run(useCase.execute({"message": "??", "userId": "client789"}))

    assert result["status"] == "ok"
    assert result["reply"] == "fallback answered: ??"
    assert fallback.messages == ["??"]
    assert knowledge.messages == []
    assert support.messages == []
