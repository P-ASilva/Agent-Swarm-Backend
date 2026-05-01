from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.adapters.outbound.postgres.userMessagePersistenceAdapter import UserMessagePersistenceAdapter
from app.domain.models import TurnDeletionSpecification
from message_persistence import MessageDatabaseMigrationRunner
from tests.integration.session_test_db import resolve_session_integration_database_url

OWNER = "guest:support-tools-test"
OWNER_B = "guest:support-tools-test-b"


def _day_range_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _day_range_end() -> datetime:
    return _day_range_start() + timedelta(days=1)


@pytest.mark.integration
def testListMessagesIncludesTurnIdAndTraceId():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    trace = str(uuid.uuid4())
    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    adapter.saveMessageTurn(
        conversationOwnerKey=OWNER,
        googleIdentity=None,
        clientUserLabel="x",
        userRequest="q",
        modelAnswer="a",
        route="knowledge",
        traceId=trace,
    )

    rows = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER,
        dayStart=_day_range_start(),
        dayEnd=_day_range_end(),
        limit=50,
    )
    assert len(rows) == 1
    assert rows[0].traceId == trace
    assert rows[0].turnId is not None
    uuid.UUID(rows[0].turnId)


@pytest.mark.integration
def testConversationProfileUpsertMerge():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    snapshot = adapter.getConversationProfile(conversationOwnerKey=OWNER)
    assert snapshot.displayName is None
    assert snapshot.metadata == {}

    adapter.upsertConversationProfile(conversationOwnerKey=OWNER, displayName="Ada")
    s1 = adapter.getConversationProfile(conversationOwnerKey=OWNER)
    assert s1.displayName == "Ada"
    assert s1.metadata == {}

    adapter.upsertConversationProfile(
        conversationOwnerKey=OWNER,
        metadataPatch={"locale": "pt-BR"},
    )
    s2 = adapter.getConversationProfile(conversationOwnerKey=OWNER)
    assert s2.displayName == "Ada"
    assert s2.metadata == {"locale": "pt-BR"}

    adapter.upsertConversationProfile(
        conversationOwnerKey=OWNER,
        metadataPatch={"phone_region": "+55"},
    )
    s3 = adapter.getConversationProfile(conversationOwnerKey=OWNER)
    assert s3.displayName == "Ada"
    assert s3.metadata == {"locale": "pt-BR", "phone_region": "+55"}

    adapter.upsertConversationProfile(conversationOwnerKey=OWNER, displayName="Ada II")
    s4 = adapter.getConversationProfile(conversationOwnerKey=OWNER)
    assert s4.displayName == "Ada II"


@pytest.mark.integration
def testDeleteMessageTurnsAllByTraceIdsByTurnIds():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    traces = [str(uuid.uuid4()) for _ in range(3)]
    for t in traces:
        adapter.saveMessageTurn(
            conversationOwnerKey=OWNER,
            googleIdentity=None,
            clientUserLabel="x",
            userRequest=f"req-{t[:8]}",
            modelAnswer="a",
            route="support",
            traceId=t,
        )

    listed = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER,
        dayStart=_day_range_start(),
        dayEnd=_day_range_end(),
        limit=50,
    )
    assert len(listed) == 3

    n_trace = adapter.deleteMessageTurns(
        conversationOwnerKey=OWNER,
        specification=TurnDeletionSpecification(kind="by_trace_ids", traceIds=(traces[0],)),
    )
    assert n_trace == 1
    remainder = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER,
        dayStart=_day_range_start(),
        dayEnd=_day_range_end(),
        limit=50,
    )
    assert len(remainder) == 2

    turnId = remainder[0].turnId
    assert turnId is not None
    n_turn = adapter.deleteMessageTurns(
        conversationOwnerKey=OWNER,
        specification=TurnDeletionSpecification(kind="by_turn_ids", turnIds=(turnId,)),
    )
    assert n_turn == 1
    remainder2 = adapter.listMessagesForDay(
        conversationOwnerKey=OWNER,
        dayStart=_day_range_start(),
        dayEnd=_day_range_end(),
        limit=50,
    )
    assert len(remainder2) == 1

    n_all = adapter.deleteMessageTurns(
        conversationOwnerKey=OWNER,
        specification=TurnDeletionSpecification(kind="all"),
    )
    assert n_all == 1
    assert (
        adapter.listMessagesForDay(
            conversationOwnerKey=OWNER,
            dayStart=_day_range_start(),
            dayEnd=_day_range_end(),
            limit=50,
        )
        == []
    )


@pytest.mark.integration
def testDeleteMessageTurnsAllScopesToOwnerKeyOnly():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    adapter = UserMessagePersistenceAdapter(databaseUrl=databaseUrl)
    for owner in (OWNER, OWNER_B):
        adapter.saveMessageTurn(
            conversationOwnerKey=owner,
            googleIdentity=None,
            clientUserLabel="x",
            userRequest="x",
            modelAnswer="y",
            route="knowledge",
            traceId=str(uuid.uuid4()),
        )

    deleted = adapter.deleteMessageTurns(
        conversationOwnerKey=OWNER,
        specification=TurnDeletionSpecification(kind="all"),
    )
    assert deleted == 1

    assert (
        len(
            adapter.listMessagesForDay(
                conversationOwnerKey=OWNER_B,
                dayStart=_day_range_start(),
                dayEnd=_day_range_end(),
                limit=50,
            )
        )
        == 1
    )
    assert (
        adapter.listMessagesForDay(
            conversationOwnerKey=OWNER,
            dayStart=_day_range_start(),
            dayEnd=_day_range_end(),
            limit=50,
        )
        == []
    )


def testDeleteMessageTurnsRejectsEmptyIdLists():
    adapter = UserMessagePersistenceAdapter(databaseUrl="postgresql://invalid:5999/nonexistent")
    with pytest.raises(ValueError):
        adapter.deleteMessageTurns(
            conversationOwnerKey=OWNER,
            specification=TurnDeletionSpecification(kind="by_turn_ids"),
        )
    with pytest.raises(ValueError):
        adapter.deleteMessageTurns(
            conversationOwnerKey=OWNER,
            specification=TurnDeletionSpecification(kind="by_trace_ids"),
        )


def testDeleteMessageTurnsRejectsMalformedTurnUuid():
    adapter = UserMessagePersistenceAdapter(databaseUrl="postgresql://invalid:5999/nonexistent")
    with pytest.raises(ValueError):
        adapter.deleteMessageTurns(
            conversationOwnerKey=OWNER,
            specification=TurnDeletionSpecification(kind="by_turn_ids", turnIds=("not-a-uuid",)),
        )
