from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import knowledge
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.core.exceptions import register_exception_handlers
from app.db.base import Base


def build_client(tmp_path) -> TestClient:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'knowledge-api.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(knowledge.router, prefix="/api/knowledge")

    def override_db_session():
        session = session_local()
        try:
            yield session
        finally:
            session.close()

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
