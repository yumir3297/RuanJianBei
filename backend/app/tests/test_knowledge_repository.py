"""``KnowledgeRepository.delete`` 的定向回归测试。

背景：``delete()`` 曾经漏写 ``await``（``AsyncSession.delete`` 是协程），提交时那条
DELETE 从未真正执行——删除接口返回 200，但数据仍在库里。API 级用例能覆盖这个症状，
这里再从仓储层钉死「删除必须落库、并且对下一个请求会话可见」。
"""

import asyncio

from sqlalchemy import func, select

from app.models.knowledge import KnowledgeEntry
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeCreate
from app.tests.async_db import open_test_session


def _payload(title: str) -> KnowledgeCreate:
    return KnowledgeCreate(
        title=title,
        category="景点信息",
        content=f"{title}的内容",
        source="自动化测试",
    )


def test_delete_removes_only_the_target_row(tmp_path) -> None:
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "delete-target.db"))
        try:
            repository = KnowledgeRepository(session)
            keep = await repository.create(_payload("保留项"))
            drop = await repository.create(_payload("待删项"))

            await repository.delete(drop)

            assert await repository.get(drop.id) is None
            assert await repository.get(keep.id) is not None
            assert await session.scalar(select(func.count(KnowledgeEntry.id))) == 1
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_delete_persists_for_the_next_request_session(tmp_path) -> None:
    """模拟线上「每个请求一个新会话」：DELETE 之后新会话必须看不到它。"""

    async def scenario():
        db_path = str(tmp_path / "delete-persist.db")

        engine, session = await open_test_session(db_path)
        created = await KnowledgeRepository(session).create(_payload("待删项"))
        created_id = created.id
        await session.close()
        await engine.dispose()

        engine, session = await open_test_session(db_path)
        repository = KnowledgeRepository(session)
        target = await repository.get(created_id)
        assert target is not None
        await repository.delete(target)
        await session.close()
        await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            assert await session.scalar(select(func.count(KnowledgeEntry.id))) == 0, "删除必须落库"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
