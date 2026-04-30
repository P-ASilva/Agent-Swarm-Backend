from __future__ import annotations

import os
from pathlib import Path

import psycopg


def _defaultSessionDatabaseUrl() -> str:
    return os.getenv(
        "SESSION_DATABASE_URL",
        "postgresql://session_swarm:session_swarm@localhost:5433/session_swarm",
    )


class MessageDatabaseMigrationRunner:
    """
    Applies SQL files from the user-messages migrations directory each time migrations run,
    relying on CREATE IF NOT EXISTS / idempotent ALTER patterns.
    """

    def __init__(self, databaseUrl: str | None = None) -> None:
        self.databaseUrl = databaseUrl or _defaultSessionDatabaseUrl()

    def applyMigrations(self, migrationsDir: str | Path = "infra/sql/user_messages") -> None:
        path = Path(migrationsDir)
        migrationFiles = sorted(path.glob("*.sql"))
        if not migrationFiles:
            raise FileNotFoundError(f"No SQL migrations found in {path}")

        with psycopg.connect(self.databaseUrl, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for migration in migrationFiles:
                    sql = migration.read_text(encoding="utf-8")
                    cursor.execute(sql)
