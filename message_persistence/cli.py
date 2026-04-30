from __future__ import annotations

import argparse

from message_persistence.store import MessageDatabaseMigrationRunner


def _buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="User message persistence migrations CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate = subparsers.add_parser("migrate", help="Apply PostgreSQL migrations for SESSION_DATABASE_URL.")
    migrate.add_argument("--migrations-dir", default="infra/sql/user_messages")
    return parser


def main() -> int:
    parser = _buildParser()
    args = parser.parse_args()
    if args.command == "migrate":
        runner = MessageDatabaseMigrationRunner()
        runner.applyMigrations(migrationsDir=args.migrations_dir)
        print("User message migrations applied successfully.")
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
