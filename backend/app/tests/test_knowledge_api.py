from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import knowledge
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.core.exceptions import register_exception_handlers
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.qa_cache import QACacheRepository
from app.tests.async_db import open_test_session


def build_client(tmp_path) -> TestClient:
    db_path = tmp_path / "knowledge-api.db"

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(knowledge.router, prefix="/api/knowledge")

    async def override_db_session():
        engine, session = await open_test_session(str(db_path))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    settings = get_settings()
    token = create_admin_token(settings.admin_token_secret)
    return {"Authorization": f"Bearer {token}"}


def knowledge_payload() -> dict[str, object]:
    return {
        "title": "测试景点",
        "category": "景点信息",
        "content": "这是用于验证知识库接口鉴权的测试内容。",
        "source": "自动化测试",
        "aliases": ["测试别名"],
    }


def test_knowledge_routes_require_admin_token(tmp_path) -> None:
    client = build_client(tmp_path)
    payload = knowledge_payload()

    responses = [
        client.get("/api/knowledge/"),
        client.post("/api/knowledge/", json=payload),
        client.put("/api/knowledge/1", json={"title": "未授权修改"}),
        client.delete("/api/knowledge/1"),
    ]

    assert all(response.status_code == 401 for response in responses)


def test_knowledge_routes_reject_invalid_token(tmp_path) -> None:
    client = build_client(tmp_path)

    response = client.get(
        "/api/knowledge/",
        headers={"Authorization": "Bearer forged-token"},
    )

    assert response.status_code == 401


def test_admin_can_manage_knowledge_entries(tmp_path) -> None:
    client = build_client(tmp_path)
    headers = admin_headers()

    create_response = client.post(
        "/api/knowledge/",
        json=knowledge_payload(),
        headers=headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    knowledge_id = created["id"]
    assert created["title"] == "测试景点"
    assert created["aliases"] == ["测试别名"]

    list_response = client.get("/api/knowledge/", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [knowledge_id]

    update_response = client.put(
        f"/api/knowledge/{knowledge_id}",
        json={"title": "已授权修改", "aliases": ["新别名"]},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "已授权修改"
    assert update_response.json()["aliases"] == ["新别名"]

    delete_response = client.delete(
        f"/api/knowledge/{knowledge_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200

    final_list_response = client.get("/api/knowledge/", headers=headers)
    assert final_list_response.status_code == 200
    assert final_list_response.json() == []


def test_delete_missing_knowledge_entry_returns_404(tmp_path) -> None:
    client = build_client(tmp_path)

    response = client.delete("/api/knowledge/9999", headers=admin_headers())

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_delete_removes_only_the_target_row(tmp_path) -> None:
    """删除必须精确命中目标行，不能连带删掉或漏删别的行。"""
    client = build_client(tmp_path)
    headers = admin_headers()

    ids = [
        client.post(
            "/api/knowledge/",
            json={
                "title": f"景点{index}",
                "category": "景点信息",
                "content": "内容",
                "source": "自动化测试",
            },
            headers=headers,
        ).json()["id"]
        for index in range(3)
    ]

    assert client.delete(f"/api/knowledge/{ids[1]}", headers=headers).status_code == 200

    remaining = {item["id"] for item in client.get("/api/knowledge/", headers=headers).json()}
    assert remaining == {ids[0], ids[2]}


def test_delete_is_not_repeatable(tmp_path) -> None:
    client = build_client(tmp_path)
    headers = admin_headers()
    created_id = client.post("/api/knowledge/", json=knowledge_payload(), headers=headers).json()["id"]

    assert client.delete(f"/api/knowledge/{created_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/knowledge/{created_id}", headers=headers).status_code == 404


def test_update_missing_knowledge_entry_returns_404(tmp_path) -> None:
    client = build_client(tmp_path)

    response = client.put("/api/knowledge/9999", json={"title": "改不到"}, headers=admin_headers())

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_create_rejects_blank_required_fields(tmp_path) -> None:
    """title/content/source 都有 min_length=1，空串必须被挡在写库之前。"""
    client = build_client(tmp_path)

    response = client.post(
        "/api/knowledge/",
        json={"title": "", "content": "", "source": ""},
        headers=admin_headers(),
    )

    assert response.status_code == 422


def test_create_publishes_knowledge_to_search_chunks(tmp_path) -> None:
    """新建知识成功后，结构化检索分块应与保存内容一致。"""
    client = build_client(tmp_path)
    response = client.post("/api/knowledge/", json=knowledge_payload(), headers=admin_headers())
    assert response.status_code == 201
    created = response.json()

    async def read_chunks():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            return await KnowledgeChunkRepository(session).list_all()
        finally:
            await session.close()
            await engine.dispose()

    chunks = asyncio.run(read_chunks())
    assert len(chunks) == 1
    assert chunks[0].source_entry_id == created["id"]
    assert chunks[0].title == created["title"]
    assert chunks[0].content == created["content"]


def test_create_rolls_back_knowledge_when_search_preparation_fails(tmp_path, monkeypatch) -> None:
    client = build_client(tmp_path)

    def fail_chunk_preparation(*_args, **_kwargs):
        raise RuntimeError("simulated chunk preparation failure")

    monkeypatch.setattr(knowledge.KnowledgeChunker, "build_chunks", fail_chunk_preparation)
    response = client.post("/api/knowledge/", json=knowledge_payload(), headers=admin_headers())
    assert response.status_code == 503
    assert response.json()["error"] == "knowledge_chunk_prepare_failed"
    assert "切块准备失败" in response.json()["message"]

    monkeypatch.undo()
    response = client.get("/api/knowledge/", headers=admin_headers())
    assert response.status_code == 200
    assert response.json() == []


def test_update_failure_keeps_previous_knowledge_and_search_chunks(tmp_path, monkeypatch) -> None:
    client = build_client(tmp_path)
    headers = admin_headers()
    created = client.post("/api/knowledge/", json=knowledge_payload(), headers=headers).json()
    original_content = created["content"]

    def fail_chunk_preparation(*_args, **_kwargs):
        raise RuntimeError("simulated chunk preparation failure")

    monkeypatch.setattr(knowledge.KnowledgeChunker, "build_chunks", fail_chunk_preparation)
    response = client.put(
        f"/api/knowledge/{created['id']}",
        json={"content": "This update must not become visible."},
        headers=headers,
    )
    assert response.status_code == 503
    assert "切块准备失败" in response.json()["message"]

    monkeypatch.undo()
    current = client.get("/api/knowledge/", headers=headers).json()[0]
    assert current["content"] == original_content

    async def read_chunks():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            return await KnowledgeChunkRepository(session).list_all()
        finally:
            await session.close()
            await engine.dispose()

    chunks = asyncio.run(read_chunks())
    assert len(chunks) == 1
    assert chunks[0].content == original_content


def test_update_invalidates_persisted_answer_cache(tmp_path) -> None:
    """知识变更后，已缓存的旧答案不能继续命中。"""
    client = build_client(tmp_path)
    headers = admin_headers()
    knowledge_id = client.post("/api/knowledge/", json=knowledge_payload(), headers=headers).json()["id"]

    async def seed_cache():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            from datetime import UTC, datetime, timedelta

            await QACacheRepository(session).set(
                "测试问题",
                "旧知识答案",
                [{"source": "自动化测试"}],
                datetime.now(UTC) + timedelta(minutes=5),
            )
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(seed_cache())
    response = client.put(
        f"/api/knowledge/{knowledge_id}",
        json={"content": "已更新的知识内容。"},
        headers=headers,
    )
    assert response.status_code == 200

    async def cache_count():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            return await QACacheRepository(session).count()
        finally:
            await session.close()
            await engine.dispose()

    assert asyncio.run(cache_count()) == 0


def test_update_replaces_search_chunks_for_knowledge_entry(tmp_path) -> None:
    client = build_client(tmp_path)
    headers = admin_headers()
    knowledge_id = client.post("/api/knowledge/", json=knowledge_payload(), headers=headers).json()["id"]
    updated_content = "更新后唯一的新内容。"

    response = client.put(
        f"/api/knowledge/{knowledge_id}",
        json={"content": updated_content},
        headers=headers,
    )
    assert response.status_code == 200

    async def read_chunks():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            return await KnowledgeChunkRepository(session).list_all()
        finally:
            await session.close()
            await engine.dispose()

    chunks = asyncio.run(read_chunks())
    assert len(chunks) == 1
    assert chunks[0].source_entry_id == knowledge_id
    assert chunks[0].content == updated_content


def test_delete_removes_search_chunks_for_knowledge_entry(tmp_path) -> None:
    client = build_client(tmp_path)
    headers = admin_headers()
    knowledge_id = client.post("/api/knowledge/", json=knowledge_payload(), headers=headers).json()["id"]

    assert client.delete(f"/api/knowledge/{knowledge_id}", headers=headers).status_code == 200

    async def read_chunk_count():
        engine, session = await open_test_session(str(tmp_path / "knowledge-api.db"))
        try:
            return len(await KnowledgeChunkRepository(session).list_all())
        finally:
            await session.close()
            await engine.dispose()

    assert asyncio.run(read_chunk_count()) == 0
