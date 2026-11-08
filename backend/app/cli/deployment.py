from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.db.deployment import initialize_database, migrate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicit database deployment actions")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("migrate", help="upgrade the schema to the single Alembic head")
    initialize = commands.add_parser("initialize", help="insert missing baseline rows")
    initialize.add_argument("--include-demo", action="store_true", help="development-only demo data")
    args = parser.parse_args(argv)
    settings = get_settings()
    if args.action == "migrate":
        migrate_database(settings)
    else:
        asyncio.run(initialize_database(settings, include_demo=args.include_demo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
