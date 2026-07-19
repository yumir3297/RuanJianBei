from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

from app.db.base import Base
from app.models import (  # noqa: F401 确保所有模型注册到 Base.metadata
    AvatarConfig,
    BehaviorSummary,
    ChatLog,
    FAQEntryRecord,
    KnowledgeChunk,
    KnowledgeEntry,
    KnowledgeBlindSpot,
    QACacheEntry,
    QuickTopic,
    RouteTemplate,
    VisitorProfile,
    VisitorFeedback,
)

config = context.config

# 读取 .env 中的 DATABASE_URL，将 asyncpg 转为 psycopg（v3）
_env_path = Path(__file__).resolve().parents[1] / ".env"
_db_url = os.environ.get("DATABASE_URL", "")
if not _db_url and _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            _db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not _db_url:
    _db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/a5_scenic_guide"
else:
    _db_url = _db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
