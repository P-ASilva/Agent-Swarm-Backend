from __future__ import annotations

from datetime import datetime

from app.application.support_operations_executor import SupportOperationsExecutor
from app.domain.models import (
    ConversationProfileSnapshot,
    GoogleIdentity,
    SupportOperation,
    TurnDeletionSpecification,
)
from app.domain.ports import UserMessagePersistencePort


class _RecordingPersistence(UserMessagePersistencePort):
    def __init__(self) -> None:
        self.upserts: list[tuple[str, dict]] = []
        self.deletes: list[tuple[str, TurnDeletionSpecification]] = []
        self.saved_turns: list[str] = []

    def listMessagesForDay(
        self,
        *,
        conversationOwnerKey: str,
        dayStart: datetime,
        dayEnd: datetime,
        limit: int = 30,
    ):
        del conversationOwnerKey, dayStart, dayEnd, limit
        return []

    def saveMessageTurn(
        self,
        *,
        conversationOwnerKey: str,
        googleIdentity: GoogleIdentity | None,
        clientUserLabel: str,
        userRequest: str,
        modelAnswer: str,
        route: str,
        traceId: str,
    ):
        del conversationOwnerKey, googleIdentity, clientUserLabel, userRequest
        del modelAnswer, route
        self.saved_turns.append(traceId)

    def getConversationProfile(self, *, conversationOwnerKey: str):
        return ConversationProfileSnapshot(
            conversationOwnerKey=conversationOwnerKey,
            displayName=None,
            metadata={},
        )

    def upsertConversationProfile(self, *, conversationOwnerKey, displayName=None, metadataPatch=None):
        self.upserts.append(
            (conversationOwnerKey, {"displayName": displayName, "metadataPatch": metadataPatch})
        )

    def deleteMessageTurns(self, *, conversationOwnerKey, specification):
        self.deletes.append((conversationOwnerKey, specification))
        return 3


def test_executor_applies_profile_and_delete_order():
    rec = _RecordingPersistence()
    ex = SupportOperationsExecutor(userMessagePersistence=rec)
    owner = "guest:u1"

    ops = (
        SupportOperation(kind="noop", payload={}),
        SupportOperation(kind="profile_patch", payload={"display_name": "Ana"}),
        SupportOperation(
            kind="delete_turns",
            payload={"scope": "by_trace_ids", "trace_ids": ["t1", "t2"]},
        ),
    )

    ex.run(conversationOwnerKey=owner, operations=ops)

    assert len(rec.upserts) == 1
    assert rec.upserts[0][0] == owner
    assert rec.upserts[0][1]["displayName"] == "Ana"

    assert len(rec.deletes) == 1
    assert rec.deletes[0][0] == owner
    assert rec.deletes[0][1].kind == "by_trace_ids"
    assert rec.deletes[0][1].traceIds == ("t1", "t2")


def test_executor_skips_when_persistence_none():
    ex = SupportOperationsExecutor(userMessagePersistence=None)
    ex.run(
        conversationOwnerKey="guest:x",
        operations=(SupportOperation(kind="profile_patch", payload={"display_name": "Z"}),),
    )
