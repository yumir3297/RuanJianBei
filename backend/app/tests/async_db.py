"""测试用的异步 SQLite 会话工厂。

本仓库持久层早已迁到异步 SQLAlchemy（`AsyncSession`），但 2026-06 前后写的一批测试
仍停留在同步 `Session` 上，一跑就报 `coroutine object has no attribute ...` 或
`ChunkedIteratorResult can't be used in 'await'`。这里把迁移所需的公共部分收敛到一处：
建异步引擎、注册 SQLite 的 ``now()`` 兼容函数、建表、返回 ``AsyncSession``。
"""

from __future__ import annotations

from datetime import UTC, datetime

import app.models  # noqa: F401  确保所有模型都已注册进 Base.metadata
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base


def _register_sqlite_now_function(engine: AsyncEngine) -> None:
    """SQLite 没有 ``now()``，而模型普遍用 ``server_default=func.now()``。

    与 ``app/db/session.py`` 对 SQLite 的处理保持一致。
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _register(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function(
            "now",
            0,
            lambda: datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds"),
        )


async def open_test_session(path: str | None = None) -> tuple[AsyncEngine, AsyncSession]:
    """建库建表并返回 ``(engine, session)``；调用方负责 ``close()`` 与 ``dispose()``。

    ``path`` 为 ``None`` 时用内存库；内存库必须配 ``StaticPool``，否则每个连接会各自
    拿到一个空库，建好的表在下一个连接里就消失了。
    """
    if path is None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")

    _register_sqlite_now_function(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine, async_sessionmaker(bind=engine, expire_on_commit=False)()
