from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import create_admin_token
from app.api import knowledge
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.core.exceptions import register_exception_handlers
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.qa_cache import QACacheRepository
from app.tests.async_db import open_test_session


def _build_client(path: str) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(knowledge.router, prefix="/api/knowledge")

    async def override_db_session():
        engine, session = await open_test_session(path)
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def _admin_headers() -> dict[str, str]:
    token = create_admin_token(get_settings().admin_token_secret)
    return {"Authorization": f"Bearer {token}"}


def _seed_published(path: str) -> int:
    async def scenario() -> int:
        engine, session = await open_test_session(path)
        from app.models.knowledge_workspace import KnowledgeState
        session.add(KnowledgeState(id=1, epoch=1))
        entry = KnowledgeEntry(
            title="已发布景点",
            category="景点信息",
            content="游客当前看到的版本",
            source="景区手册",
            aliases="旧别名",
        )
        session.add(entry)
        await session.flush()
        revision = KnowledgeRevision(
            id="published-revision-1",
            knowledge_entry_id=entry.id,
            title=entry.title,
            category=entry.category,
            content=entry.content,
            source=entry.source,
            aliases=entry.aliases,
        )
        session.add(revision)
        await session.flush()
        entry.published_revision_id = revision.id
        await session.commit()
        entry_id = entry.id
        await session.close()
        await engine.dispose()
        return entry_id

    return asyncio.run(scenario())


def _search(path: str, query: str):
    async def scenario():
        engine, session = await open_test_session(path)
        try:
            return await KnowledgeRepository(session).search(query)
        finally:
            await session.close()
            await engine.dispose()

    return asyncio.run(scenario())


def test_new_knowledge_is_saved_as_persistent_draft_and_hidden_from_tourists(tmp_path) -> None:
    db_path = str(tmp_path / "draft.db")
    client = _build_client(db_path)

    response = client.post(
        "/api/knowledge/",
        headers=_admin_headers(),
        json={
            "title": "新导览点",
            "category": "景点信息",
            "content": "等待审核的介绍",
            "source": "新 PDF 第 2 页",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["content"] == "等待审核的介绍"
    assert _search(db_path, "新导览点") == []

    async def restored_draft():
        engine, session = await open_test_session(db_path)
        try:
            entry = await session.get(KnowledgeEntry, created["id"])
            assert entry is not None
            assert entry.published_revision_id is None
            revision = await session.get(KnowledgeRevision, entry.draft_revision_id)
            assert revision is not None
            assert revision.content == "等待审核的介绍"
            assert revision.source == "新 PDF 第 2 页"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(restored_draft())


def test_edit_keeps_old_published_content_visible_until_publish(tmp_path) -> None:
    db_path = str(tmp_path / "edit.db")
    entry_id = _seed_published(db_path)
    client = _build_client(db_path)

    response = client.put(
        f"/api/knowledge/{entry_id}",
        headers=_admin_headers(),
        json={"title": "审核中的景点名称", "content": "准备发布的新介绍", "expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "准备发布的新介绍"
    visible = _search(db_path, "游客当前看到")
    assert len(visible) == 1
    assert visible[0].content == "游客当前看到的版本"

    stale = client.put(
        f"/api/knowledge/{entry_id}",
        headers=_admin_headers(),
        json={"content": "覆盖他人修改", "expected_version": 1},
    )
    assert stale.status_code == 409


def test_discarding_draft_preserves_the_published_version(tmp_path) -> None:
    db_path = str(tmp_path / "discard.db")
    entry_id = _seed_published(db_path)
    client = _build_client(db_path)
    update = client.put(
        f"/api/knowledge/{entry_id}",
        headers=_admin_headers(),
        json={"content": "后来放弃的修改", "expected_version": 1},
    )
    assert update.status_code == 200

    response = client.delete(f"/api/knowledge/{entry_id}/draft", headers=_admin_headers())

    assert response.status_code == 200
    visible = _search(db_path, "游客当前看到")
    assert len(visible) == 1
    assert visible[0].content == "游客当前看到的版本"
    admin_entry = client.get("/api/knowledge/", headers=_admin_headers()).json()[0]
    assert admin_entry["content"] == "游客当前看到的版本"
    assert admin_entry["draft_revision_id"] is None

    new_entry = client.post(
        "/api/knowledge/",
        headers=_admin_headers(),
        json={"title": "未发布的新条目", "category": "景点信息", "content": "临时内容", "source": "测试"},
    ).json()
    edited = client.put(
        f"/api/knowledge/{new_entry['id']}",
        headers=_admin_headers(),
        json={"content": "修改后再丢弃", "expected_version": new_entry["lock_version"]},
    )
    assert edited.status_code == 200
    discarded = client.delete(f"/api/knowledge/{new_entry['id']}/draft", headers=_admin_headers())
    assert discarded.status_code == 200
    assert all(item["id"] != new_entry["id"] for item in client.get("/api/knowledge/", headers=_admin_headers()).json())
    assert _search(db_path, "未发布的新条目") == []


def test_delete_withdraws_without_erasing_revision_and_invalidates_answer_cache(tmp_path) -> None:
    db_path = str(tmp_path / "withdraw.db")
    entry_id = _seed_published(db_path)
    client = _build_client(db_path)

    async def seed_cache():
        engine, session = await open_test_session(db_path)
        try:
            await QACacheRepository(session).set(
                "景点是什么",
                "旧答案",
                [{"source": "已发布景点"}],
                datetime.now(UTC) + timedelta(minutes=10),
            )
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(seed_cache())
    response = client.delete(f"/api/knowledge/{entry_id}", headers=_admin_headers())

    assert response.status_code == 200
    assert _search(db_path, "已发布景点") == []
    cannot_restore = client.put(
        f"/api/knowledge/{entry_id}",
        headers=_admin_headers(),
        json={"content": "旧导入任务试图恢复", "expected_version": 2},
    )
    assert cannot_restore.status_code == 409

    async def verify_state():
        engine, session = await open_test_session(db_path)
        try:
            entry = await session.get(KnowledgeEntry, entry_id)
            assert entry is not None
            assert entry.published_revision_id is None
            assert entry.withdrawn_at is not None
            assert await session.get(KnowledgeRevision, "published-revision-1") is not None
            state = await session.get(KnowledgeState, 1)
            assert state is not None and state.epoch == 2
            assert await QACacheRepository(session).count() == 0
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(verify_state())
