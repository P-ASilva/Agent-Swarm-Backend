from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.adapters.outbound.postgres.userMessagePersistenceAdapter import UserMessagePersistenceAdapter
from app.application.support_operations_executor import SupportOperationsExecutor
from app.domain.models import SupportOperation
from message_persistence import MessageDatabaseMigrationRunner
from tests.integration.session_test_db import resolve_session_integration_database_url

OWNER_EXEC = "guest:support-tool-executor-owner"
OWNER_OTHER = "guest:support-tool-executor-other"


def _truncate(databaseUrl: str) -> None:
    with psycopg.connect(databaseUrl, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )


def _day_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _day_end() -> datetime:
    return _day_start() + timedelta(days=1)


@pytest.mark.integration
def testSupportExecutorAppliesProfilePatchAndDeletesOnRealDb():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    _truncate(databaseUrl)
    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    executor = SupportOperationsExecutor(userMessagePersistence=adapter)

    t1 = str(uuid.uuid4())
    t2 = str(uuid.uuid4())
    for tid in (t1, t2):
        adapter.saveMessageTurn(
            conversationOwnerKey=OWNER_EXEC,
            googleIdentity=None,
            clientUserLabel="u",
            userRequest=f"req-{tid[:6]}",
            modelAnswer="ans",
            route="support",
            traceId=tid,
        )

    listed = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER_EXEC,
        dayStart=_day_start(),
        dayEnd=_day_end(),
        limit=50,
    )
    assert len(listed) == 2
    turnId = listed[0].turnId
    assert turnId is not None

    ops = (
        SupportOperation(
            kind="profile_patch",
            payload={"display_name": "ExecutorUser", "profile_metadata": {"tier": "test"}},
        ),
        SupportOperation(
            kind="delete_turns",
            payload={"scope": "by_turn_ids", "turn_ids": [turnId]},
        ),
    )
    executor.run(conversationOwnerKey=OWNER_EXEC, operations=ops)

    profile = adapter.getConversationProfile(conversationOwnerKey=OWNER_EXEC)
    assert profile.displayName == "ExecutorUser"
    assert profile.metadata.get("tier") == "test"

    remaining = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER_EXEC,
        dayStart=_day_start(),
        dayEnd=_day_end(),
        limit=50,
    )
    assert len(remaining) == 1
    executor.run(
        conversationOwnerKey=OWNER_EXEC,
        operations=(SupportOperation(kind="delete_turns", payload={"scope": "all"}),),
    )
    assert (
        adapter.listMessagesForDay(
            conversationOwnerKey=OWNER_EXEC,
            dayStart=_day_start(),
            dayEnd=_day_end(),
            limit=50,
        )
        == []
    )


@pytest.mark.integration
def testSupportExecutorScopedDeleteLeavesOtherOwnersRows():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    _truncate(databaseUrl)
    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    executor = SupportOperationsExecutor(userMessagePersistence=adapter)

    for owner in (OWNER_EXEC, OWNER_OTHER):
        adapter.saveMessageTurn(
            conversationOwnerKey=owner,
            googleIdentity=None,
            clientUserLabel="u",
            userRequest=f"same-text-{owner[-4:]}",
            modelAnswer="a",
            route="support",
            traceId=str(uuid.uuid4()),
        )

    executor.run(
        conversationOwnerKey=OWNER_EXEC,
        operations=(SupportOperation(kind="delete_turns", payload={"scope": "all"}),),
    )

    assert (
        len(
            adapter.listMessagesForDay(
                conversationOwnerKey=OWNER_OTHER,
                dayStart=_day_start(),
                dayEnd=_day_end(),
                limit=50,
            )
        )
        == 1
    )
    assert (
        adapter.listMessagesForDay(
            conversationOwnerKey=OWNER_EXEC,
            dayStart=_day_start(),
            dayEnd=_day_end(),
            limit=50,
        )
        == []
    )


@pytest.mark.integration
def testSupportExecutorMalformedDeleteScopeSkipsQuietlyStillRunsOtherOps():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    _truncate(databaseUrl)
    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    executor = SupportOperationsExecutor(userMessagePersistence=adapter)

    adapter.saveMessageTurn(
        conversationOwnerKey=OWNER_EXEC,
        googleIdentity=None,
        clientUserLabel="u",
        userRequest="persist",
        modelAnswer="a",
        route="support",
        traceId=str(uuid.uuid4()),
    )

    ops = (
        SupportOperation(kind="delete_turns", payload={"scope": "unknown_scope"}),
        SupportOperation(
            kind="profile_patch",
            payload={"display_name": "StillWritten"},
        ),
    )
    executor.run(conversationOwnerKey=OWNER_EXEC, operations=ops)

    snapshot = adapter.getConversationProfile(conversationOwnerKey=OWNER_EXEC)
    assert snapshot.displayName == "StillWritten"
    rows = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER_EXEC,
        dayStart=_day_start(),
        dayEnd=_day_end(),
        limit=50,
    )
    assert len(rows) == 1
