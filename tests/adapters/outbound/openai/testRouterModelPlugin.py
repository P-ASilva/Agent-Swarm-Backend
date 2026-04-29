from app.adapters.outbound.openai import OpenAiRouterModelPlugin


class FakeOpenAiChat:
    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error

    def chatCompletion(self, **kwargs):  # noqa: ANN003
        del kwargs
        if self.error is not None:
            raise self.error
        return self.content or '{"route":"fallback","rationale":"empty"}'


def testRouterModelPluginUsesModelFromEnv(monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "gpt-4o-mini")
    plugin = OpenAiRouterModelPlugin(openAiChat=FakeOpenAiChat('{"route":"knowledge","rationale":"facts"}'))

    decision = plugin.decideRoute("How does it work?")

    assert decision.route == "knowledge"
    assert decision.usedModel == "gpt-4o-mini"
    assert decision.degraded is False


def testRouterModelPluginFallsBackWhenModelMissing(monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "")
    plugin = OpenAiRouterModelPlugin(openAiChat=FakeOpenAiChat('{"route":"support","rationale":"help"}'))

    decision = plugin.decideRoute("help")

    assert decision.route == "fallback"
    assert decision.degraded is True


def testRouterModelPluginFallsBackOnOpenAiError(monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "gpt-4o-mini")
    plugin = OpenAiRouterModelPlugin(openAiChat=FakeOpenAiChat(error=RuntimeError("boom")))

    decision = plugin.decideRoute("hello")

    assert decision.route == "fallback"
    assert decision.degraded is True
