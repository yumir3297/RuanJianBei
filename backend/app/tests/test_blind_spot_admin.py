import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import admin
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.core.exceptions import register_exception_handlers
from app.models.faq import FAQEntryRecord
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.services.qa.faq_matcher import FAQMatcher
from app.tests.async_db import open_test_session


def build_client(db_path, monkeypatch):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(admin.router, prefix="/api/admin")

    async def override_db_session():
        engine, session = await open_test_session(str(db_path))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session

    async def fake_reload_runtime_faq_matcher(session):
        return 7.5

    monkeypatch.setattr(admin, "reload_runtime_faq_matcher", fake_reload_runtime_faq_matcher)
    monkeypatch.setattr(
        admin,
        "get_runtime_faq_stats",
        lambda: {"entry_count": 89, "semantic_alias_count": 205},
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {create_admin_token(get_settings().admin_token_secret)}"})
    return client


def test_admin_lists_and_resolves_blind_spot_with_faq(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "blind-spot-admin.db"
    client = build_client(db_path, monkeypatch)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session))
            primary = await tracker.record(raw_query="卫生间在哪里", normalized_query="卫生间在哪里")
            await tracker.record(raw_query="景区厕所在哪", normalized_query="卫生间在哪里")
            await tracker.record(raw_query="哪里可以租充电宝", normalized_query="哪里可以租充电宝")
            return primary.id
        finally:
            await session.close()
            await engine.dispose()

    primary_id = asyncio.run(scenario())

    list_response = client.get("/api/admin/blind-spots", params={"status": "open", "limit": 10})
    assert list_response.status_code == 200
    assert [item["hit_count"] for item in list_response.json()] == [2, 1]
    assert list_response.json()[0]["raw_query_samples"] == ["卫生间在哪里", "景区厕所在哪"]

    payload = {
        "faq_id": "faq_admin_restroom_001",
        "category": "实用信息",
        "aliases": ["景区卫生间位置"],
        "answer": "卫生间位置信息请以景区现场导览标识为准。",
        "sources": ["景区运营后台人工核验"],
    }
    resolve_response = client.post(
        f"/api/admin/blind-spots/{primary_id}/resolve-with-faq",
        json=payload,
    )

    assert resolve_response.status_code == 200
    body = resolve_response.json()
    assert body["blind_spot"]["status"] == "resolved"
    assert body["blind_spot"]["resolution_type"] == "faq"
    assert body["faq_id"] == "faq_admin_restroom_001"
    assert body["faq_reload_ms"] == 7.5
    assert body["faq_index_count"] == 89
    assert body["semantic_alias_count"] == 205

    async def verify():
        engine, session = await open_test_session(str(db_path))
        try:
            blind_spot = await session.get(KnowledgeBlindSpot, primary_id)
            faq = await session.get(FAQEntryRecord, "faq_admin_restroom_001")
            assert blind_spot is not None
            assert blind_spot.resolved_faq_id == "faq_admin_restroom_001"
            assert blind_spot.category == "实用信息"
            assert blind_spot.resolved_at is not None
            assert faq is not None
            assert json.loads(faq.aliases_json) == [
                "景区卫生间位置",
                "卫生间在哪里",
                "景区厕所在哪",
            ]
            assert json.loads(faq.sources_json) == ["景区运营后台人工核验"]
            matcher = FAQMatcher()
            await matcher.load_from_db(session)
            assert matcher.match("卫生间在哪里").entry.id == "faq_admin_restroom_001"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(verify())

    resolved_response = client.get("/api/admin/blind-spots", params={"status": "resolved"})
    assert resolved_response.status_code == 200
    assert [item["id"] for item in resolved_response.json()] == [primary_id]


def test_resolve_with_faq_updates_existing_faq_and_validates_input(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "blind-spot-admin.db"
    client = build_client(db_path, monkeypatch)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session))
            blind_spot = await tracker.record(raw_query="母婴室在哪里", normalized_query="母婴室在哪里")
            blind_spot_id = blind_spot.id
            session.add(
                FAQEntryRecord(
                    id="faq_admin_service_001",
                    category="旧分类",
                    aliases_json='["旧问法"]',
                    answer="旧答案",
                    sources_json='["旧来源"]',
                )
            )
            await session.commit()
            return blind_spot_id
        finally:
            await session.close()
            await engine.dispose()

    blind_spot_id = asyncio.run(scenario())

    invalid_response = client.post(
        f"/api/admin/blind-spots/{blind_spot_id}/resolve-with-faq",
        json={
            "faq_id": "faq_admin_service_001",
            "category": "实用信息",
            "aliases": ["母婴室位置"],
            "answer": "请查看现场标识。",
            "sources": ["   "],
        },
    )
    assert invalid_response.status_code == 422

    update_response = client.post(
        f"/api/admin/blind-spots/{blind_spot_id}/resolve-with-faq",
        json={
            "faq_id": "faq_admin_service_001",
            "category": "实用信息",
            "aliases": ["母婴室位置"],
            "answer": "母婴室位置请以现场服务台说明为准。",
            "sources": ["景区服务台人工核验"],
        },
    )
    assert update_response.status_code == 200

    async def verify():
        engine, session = await open_test_session(str(db_path))
        try:
            faq = await session.scalar(select(FAQEntryRecord).where(FAQEntryRecord.id == "faq_admin_service_001"))
            assert faq is not None
            assert faq.category == "实用信息"
            assert faq.answer == "母婴室位置请以现场服务台说明为准。"
            assert json.loads(faq.aliases_json) == ["母婴室位置", "母婴室在哪里"]
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(verify())

    missing_response = client.post(
        "/api/admin/blind-spots/99999/resolve-with-faq",
        json={
            "faq_id": "faq_missing",
            "category": "实用信息",
            "aliases": ["不存在"],
            "answer": "不存在",
            "sources": ["人工核验"],
        },
    )
    assert missing_response.status_code == 404
