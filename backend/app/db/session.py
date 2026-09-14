from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


settings = get_settings()

engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "echo": False,
}

# SQLite (used by the self-contained reviewer package) does not accept the
# PostgreSQL connection-pool sizing options. Keep them for PostgreSQL while
# allowing DATABASE_URL to switch to sqlite+aiosqlite without code changes.
if not settings.database_url.startswith("sqlite"):
    engine_options.update(
        pool_size=20,
        max_overflow=10,
    )

engine = create_async_engine(
    settings.database_url,
    **engine_options,
)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_now_function(dbapi_connection, _connection_record) -> None:
        """Support the historical Alembic ``now()`` defaults in SQLite.

        PostgreSQL provides ``now()`` natively. The reviewer database uses
        SQLite, whose equivalent is ``CURRENT_TIMESTAMP``; registering this
        small compatibility function keeps the existing PostgreSQL migration
        schema usable without changing its production behavior.
        """
        dbapi_connection.create_function(
            "now",
            0,
            lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
                sep=" ",
                timespec="seconds",
            ),
        )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
