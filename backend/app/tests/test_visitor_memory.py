import asyncio
from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.visitor_memory import VisitorMemory  # noqa: F401  确保模型已注册
from app.repositories.visitor_memory import VisitorMemoryRepository


async def _make_session():
    """自带内存 SQLite，不依赖既有 fixture。

    只建 visitor_memories 一张表：其它模型在同一个 pytest 进程里可能已被其它测试模块
    导入，全量 create_all 会把它们一并建到 SQLite 上，引入无关噪声。
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_now(dbapi_connection, _record):
        dbapi_connection.create_function(
            "now", 0, lambda: datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
        )

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: VisitorMemory.__table__.create(sync_conn))
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine, maker()


def test_record_visit_accumulates_across_sessions():
    async def scenario():
        engine, session = await _make_session()
        try:
            repo = VisitorMemoryRepository(session)
            first = await repo.record_visit(
                visitor_id="v-1",
                session_id="s-1",
                attraction_title="灵山大佛",
                interests=["大佛", "佛教文化"],
                narration_audience="child",
            )
            assert first.visit_count == 1

            second = await repo.record_visit(
                visitor_id="v-1",
                session_id="s-1",
                attraction_title="灵山梵宫",
                interests=["建筑"],
                narration_audience="child",
            )
            assert second.visit_count == 1, "同一会话内多轮不应重复计次"

            third = await repo.record_visit(
                visitor_id="v-1",
                session_id="s-2",
                attraction_title="九龙灌浴",
                interests=["九龙灌浴"],
                narration_audience="adult",
            )
            assert third.visit_count == 2, "换会话应计一次新到访"

            decoded = VisitorMemoryRepository.decode(third)
            assert decoded["visited_attractions"] == ["灵山大佛", "灵山梵宫", "九龙灌浴"]
            assert "大佛" in decoded["preference_tags"]
            assert "建筑" in decoded["preference_tags"]
            assert decoded["narration_audience"] == "adult"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_visited_attractions_are_deduplicated():
    async def scenario():
        engine, session = await _make_session()
        try:
            repo = VisitorMemoryRepository(session)
            await repo.record_visit(visitor_id="v-2", session_id="s-1", attraction_title="灵山大佛")
            again = await repo.record_visit(
                visitor_id="v-2", session_id="s-2", attraction_title="灵山大佛"
            )
            assert VisitorMemoryRepository.decode(again)["visited_attractions"] == ["灵山大佛"]
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_memory_is_isolated_by_site():
    async def scenario():
        engine, session = await _make_session()
        try:
            repo = VisitorMemoryRepository(session)
            await repo.record_visit(
                visitor_id="v-3",
                site_id="lingshan",
                session_id="s-1",
                attraction_title="灵山大佛",
            )
            other = await repo.get("v-3", site_id="other-park")
            assert other is None
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_delete_removes_memory():
    async def scenario():
        engine, session = await _make_session()
        try:
            repo = VisitorMemoryRepository(session)
            await repo.record_visit(
                visitor_id="v-4", session_id="s-1", attraction_title="灵山大佛"
            )
            removed = await repo.delete("v-4")
            assert removed == 1
            assert await repo.get("v-4") is None
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
