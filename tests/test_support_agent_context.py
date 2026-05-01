from __future__ import annotations

import json

from app.application.agents.supportAgent import SupportAgent
from app.application.support_execution_context import supportConversationOwnerKeyContext
from app.application.support_operations_executor import SupportOperationsExecutor
from app.domain.models import ConversationProfileSnapshot


class _FailChat:
    def chatCompletion(self, **kwargs):
        raise AssertionError("should not call model without execution context")


def test_support_agent_refuses_when_owner_context_missing():
    agent = SupportAgent(
        openAiChat=_FailChat(),
        executor=SupportOperationsExecutor(userMessagePersistence=None),
    )
    reply = agent.handleMessage("preciso apagar histórico")
    assert "contexto" in reply.lower()


class _StubPersistenceFull:
    def __init__(self) -> None:
        self._snap = ConversationProfileSnapshot(
            conversationOwnerKey="guest:owner-test",
            displayName="Ana Teste",
            metadata={"nivel": "basico"},
        )

    def getConversationProfile(self, *, conversationOwnerKey: str) -> ConversationProfileSnapshot:
        del conversationOwnerKey
        return self._snap

    def upsertConversationProfile(
        self,
        *,
        conversationOwnerKey: str,
        displayName: str | None = None,
        metadataPatch: dict | None = None,
    ) -> None:
        del conversationOwnerKey
        meta = dict(self._snap.metadata)
        if metadataPatch:
            meta.update(metadataPatch)
        dn = displayName if displayName is not None else self._snap.displayName
        self._snap = ConversationProfileSnapshot(
            conversationOwnerKey=self._snap.conversationOwnerKey,
            displayName=dn,
            metadata=meta,
        )

    def listMessagesForDay(self, **kwargs):
        del kwargs
        return []

    def saveMessageTurn(self, **kwargs):
        del kwargs

    def deleteMessageTurns(self, **kwargs):
        del kwargs
        return 0


class _CaptureChat:
    def __init__(self) -> None:
        self.capturedMessages: list[dict[str, str]] | None = None

    def chatCompletion(self, *, messages, **kwargs):
        del kwargs
        self.capturedMessages = list(messages)
        return json.dumps(
            {
                "assistant_reply": "Segue o que temos registado.",
                "operations": [{"kind": "noop", "payload": {}}],
            }
        )


def test_support_agent_injects_profile_and_appends_confirmed_block():
    persistence = _StubPersistenceFull()
    chat = _CaptureChat()
    agent = SupportAgent(
        openAiChat=chat,
        executor=SupportOperationsExecutor(userMessagePersistence=persistence),
    )
    token = supportConversationOwnerKeyContext.set("guest:owner-test")
    try:
        reply = agent.handleMessage("quais os meus dados?")
    finally:
        supportConversationOwnerKeyContext.reset(token)

    assert chat.capturedMessages is not None
    profile_system = next(
        m["content"]
        for m in chat.capturedMessages
        if m["content"].startswith("PERFIL_ATUAL (fonte:")
    )
    assert "Ana Teste" in profile_system
    assert "basico" in profile_system
    assert "Dados confirmados no seu perfil" in reply
    assert "Ana Teste" in reply


def test_support_agent_profile_patch_updates_disclosure():
    persistence = _StubPersistenceFull()
    chat = _CaptureChatAdaptive()
    agent = SupportAgent(
        openAiChat=chat,
        executor=SupportOperationsExecutor(userMessagePersistence=persistence),
    )
    token = supportConversationOwnerKeyContext.set("guest:owner-test")
    try:
        reply = agent.handleMessage("chame-me João")
    finally:
        supportConversationOwnerKeyContext.reset(token)

    assert "João" in reply
    assert persistence._snap.displayName == "João"


class _CaptureChatAdaptive:
    def chatCompletion(self, *, messages, **kwargs):
        del kwargs, messages
        return json.dumps(
            {
                "assistant_reply": "Atualizei o nome exibido.",
                "operations": [
                    {
                        "kind": "profile_patch",
                        "payload": {"display_name": "João"},
                    }
                ],
            }
        )
