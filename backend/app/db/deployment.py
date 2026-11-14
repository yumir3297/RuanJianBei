from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.core.config import Settings
from app.db.bootstrap import (
    bootstrap_avatar_configs,
    bootstrap_experience_demo_feedback,
    bootstrap_quick_topics,
    bootstrap_sample_data,
)


def migration_database_url(settings: Settings) -> str:
    url = settings.database_url.strip()
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://").replace(
        "sqlite+aiosqlite://", "sqlite://"
    )


def _alembic_config(settings: Settings) -> Config:
    backend_root = settings.backend_root
    config_path = backend_root / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("prepend_sys_path", str(backend_root).replace("%", "%%"))
    config.set_main_option("sqlalchemy.url", migration_database_url(settings).replace("%", "%%"))
    return config


def migrate_database(settings: Settings) -> None:
    """Apply Alembic migrations explicitly using the supplied database settings."""
    command.upgrade(_alembic_config(settings), "head")


def check_schema_head(settings: Settings) -> str:
    """Fail closed unless the database is at the repository's single Alembic head."""
    config = _alembic_config(settings)
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected one schema revision head; found {len(heads)}")
    engine = create_engine(migration_database_url(settings), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
    except Exception as exc:
        raise RuntimeError("Could not read database schema revision") from exc
    finally:
        engine.dispose()
    if current != heads[0]:
        raise RuntimeError(f"Database schema revision {current!r} does not match application head {heads[0]!r}")
    return current


async def initialize_database(settings: Settings, *, include_demo: bool = False) -> None:
    """Insert only idempotent baseline rows; demo rows are development-only and opt-in."""
    await bootstrap_quick_topics()
    await bootstrap_avatar_configs()
    is_development = settings.app_env.strip().lower() in {"development", "dev", "test"}
    if include_demo and is_development and settings.enable_sample_data:
        await bootstrap_sample_data()
        await bootstrap_experience_demo_feedback()


async def prepare_startup_database(
    settings: Settings,
    *,
    migrate: Callable[[Settings], None] | None = None,
    initialize: Callable[..., Awaitable[None]] | None = None,
) -> None:
    """Keep the legacy development startup behavior configurable and production explicit."""
    if settings.auto_migrate_on_startup:
        (migrate or migrate_database)(settings)
    else:
        check_schema_head(settings)
    if settings.bootstrap_on_startup:
        initializer = initialize or initialize_database
        is_development = settings.app_env.strip().lower() in {"development", "dev", "test"}
        include_demo = is_development and settings.enable_sample_data
        await initializer(settings, include_demo=include_demo)


def legacy_frontend_dist(settings: Settings) -> Path:
    return settings.project_root / "frontend" / "dist"
