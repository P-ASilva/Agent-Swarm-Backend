import pytest

from app.adapters.outbound.openai import OpenAiChatAdapter


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def testOpenAiChatAdapterFromEnvUsesOpenAiApiKey(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "4.5")

    adapter = OpenAiChatAdapter.fromEnv()

    assert adapter.apiKey == "test-key"
    assert adapter.timeoutSeconds == 4.5


def testOpenAiChatAdapterRequiresApiKey():
    adapter = OpenAiChatAdapter(apiKey="")

    with pytest.raises(RuntimeError):
        adapter.chatCompletion(messages=[], model="gpt-4o-mini")


def testOpenAiChatAdapterReturnsContentFromResponse(monkeypatch):
    def fakePost(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return FakeResponse(
            {"choices": [{"message": {"content": '{"route":"knowledge","rationale":"ok"}'}}]}
        )

    monkeypatch.setattr("app.adapters.outbound.openai.openAiChatAdapter.httpx.post", fakePost)
    adapter = OpenAiChatAdapter(apiKey="test-key")

    content = adapter.chatCompletion(
        messages=[{"role": "user", "content": "hello"}],
        model="gpt-4o-mini",
        responseFormat={"type": "json_object"},
    )

    assert '"route":"knowledge"' in content
