from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.guardrails import NoOpGuardrailsAdapter
from app.adapters.outbound.postgres.userMessagePersistenceAdapter import UserMessagePersistenceAdapter
from app.application.usecase import MessageUseCase
from app.domain.models import GoogleIdentity, RouterDecision
from app.domain.ports import InvalidGoogleTokenError
from app.main import createApp
from message_persistence import MessageDatabaseMigrationRunner
from tests.integration.session_test_db import resolve_session_integration_database_url


class StubGoogleTokenVerifier:
    def verifyIdToken(self, idToken: str) -> GoogleIdentity:
        if idToken != "valid-google-token":
            raise InvalidGoogleTokenError("invalid token")
        return GoogleIdentity(
            subject="google-subject-msg-001",
            email="messages@example.com",
            issuer="https://accounts.google.com",
            audience="test-client-id",
        )


class ForcedSupportRouter:
    def decideRoute(self, message: str) -> RouterDecision:
        del message
        return RouterDecision(route="support", rationale="forced")


class InspectingAgent:
    def __init__(self) -> None:
        self.receivedMessages: list[str] = []

    def handleMessage(self, message: str) -> str:
        self.receivedMessages.append(message)
        return "ACK"


class UnreachableKnowledgeAgent:
    def handleMessage(self, message: str) -> str:
        raise AssertionError("knowledge agent should not run in this test")


class UnreachableSwarmAgent:
    def handleMessage(self, message: str) -> str:
        raise AssertionError("swarm agent should not run in this test")


@pytest.mark.integration
def testGoogleAuthenticatedMessagesPersistAndLoadDailyContext():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping Google persistence test due unavailable test DB: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    agent = InspectingAgent()
    useCase = MessageUseCase(
        knowledgeAgent=UnreachableKnowledgeAgent(),
        supportAgent=agent,
        swarmKnowledgeAgent=UnreachableSwarmAgent(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=ForcedSupportRouter(),
        googleTokenVerifier=StubGoogleTokenVerifier(),
        userMessagePersistence=UserMessagePersistenceAdapter(databaseUrl=databaseUrl),
    )
    client = TestClient(createApp(messageUseCase=useCase))

    first = client.post(
        "/messages",
        json={"message": "first user request", "userId": "playground-user", "googleIdToken": "valid-google-token"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/messages",
        json={"message": "second user request", "userId": "playground-user", "googleIdToken": "valid-google-token"},
    )
    assert second.status_code == 200, second.text

    assert len(agent.receivedMessages) == 2
    assert "Histórico da conversa de hoje" in agent.receivedMessages[1]
    assert "usuário: first user request" in agent.receivedMessages[1]
    assert "assistente: ACK" in agent.receivedMessages[1]

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM app_users")
            usersCount = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM user_message_turns")
            messagesCount = int(cursor.fetchone()[0])

    assert usersCount == 1
    assert messagesCount == 2


@pytest.mark.integration
def testGuestMessagesPersistWithoutGoogleToken():
    databaseUrl = resolve_session_integration_database_url()

    migrations = MessageDatabaseMigrationRunner(databaseUrl=databaseUrl)
    try:
        migrations.applyMigrations()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Skipping guest persistence test due unavailable test DB: {exc}")

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE user_message_turns, conversation_profiles, app_users CASCADE",
            )

    useCase = MessageUseCase(
        knowledgeAgent=UnreachableKnowledgeAgent(),
        supportAgent=InspectingAgent(),
        swarmKnowledgeAgent=UnreachableSwarmAgent(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=ForcedSupportRouter(),
        userMessagePersistence=UserMessagePersistenceAdapter(databaseUrl=databaseUrl),
    )
    client = TestClient(createApp(messageUseCase=useCase))

    first = client.post(
        "/messages",
        json={"message": "hello guest", "userId": "guest-unit-a"},
    )
    second = client.post(
        "/messages",
        json={"message": "second guest turn", "userId": "guest-unit-a"},
    )
    assert first.status_code == 200 and second.status_code == 200

    with psycopg.connect(databaseUrl, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM user_message_turns WHERE conversation_owner_key = %s", ("guest:guest-unit-a",))
            assert int(cursor.fetchone()[0]) == 2


@pytest.mark.integration
def testMessagesRejectInvalidGoogleToken():
    useCase = MessageUseCase(
        knowledgeAgent=UnreachableKnowledgeAgent(),
        supportAgent=InspectingAgent(),
        swarmKnowledgeAgent=UnreachableSwarmAgent(),
        messageGuardrails=NoOpGuardrailsAdapter(),
        routerModel=ForcedSupportRouter(),
        googleTokenVerifier=StubGoogleTokenVerifier(),
        userMessagePersistence=UserMessagePersistenceAdapter(
            databaseUrl=resolve_session_integration_database_url(),
        ),
    )
    client = TestClient(createApp(messageUseCase=useCase))

    response = client.post(
        "/messages",
        json={"message": "hello", "userId": "playground-user", "googleIdToken": "bad-token"},
    )
    assert response.status_code == 401
