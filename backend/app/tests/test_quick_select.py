import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.quick_select import router
from app.core.deps import get_db_session
from app.db.base import Base
from app.db.bootstrap import seed_quick_topics
from app.models.knowledge import KnowledgeEntry
from app.models.quick_topic import QuickTopic
from app.models.route import RouteTemplate
from app.schemas.chat import ChatRequest


def test_chat_request_accepts_optional_selection_context() -> None:
    request = ChatRequest(
        query="介绍一下灵山大佛",
        session_id="selection-test",
        selection={
            "mode": "attraction",
            "attraction_id": 13,
            "topic_key": "history",
            "interests": ["历史文化"],
        },
    )

    assert request.selection is not None
    assert request.selection.attraction_id == 13
    assert request.selection.interests == ["历史文化"]


def test_quick_select_bootstrap_uses_existing_knowledge_and_routes(tmp_path) -> None:
    db_path = tmp_path / "quick-select.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session = session_local()
    try:
        assert seed_quick_topics(session) == 8
        assert seed_quick_topics(session) == 0

        disabled_topic = session.get(QuickTopic, "dining")
        assert disabled_topic is not None
        disabled_topic.is_enabled = False
        session.add_all(
            [
                KnowledgeEntry(
                    title="灵山大佛",
                    category="景点信息",
                    content="官方景点资料",
                    source="official.docx",
                    aliases="大佛",
                    metadata_json=json.dumps(
                        {"scenic_area": "灵山胜境", "attraction_id": "LS-011"},
                        ensure_ascii=False,
                    ),
                ),
                KnowledgeEntry(
                    title="景区历史",
                    category="历史文化",
                    content="官方历史资料",
                    source="official.docx",
                    aliases="",
                ),
                RouteTemplate(
                    id="route_001",
                    title="历史文化路线",
                    duration_label="6小时深度游",
                    route_plan="入口 -> 灵山大佛",
                    source="official.docx",
                    tags="历史|文化",
                ),
            ]
        )
        session.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api/quick-select")

        def override_db_session():
            test_session = session_local()
            try:
                yield test_session
            finally:
                test_session.close()

        app.dependency_overrides[get_db_session] = override_db_session
        response = TestClient(app).get("/api/quick-select/bootstrap")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["topics"]) == 7
        assert "dining" not in {topic["key"] for topic in payload["topics"]}
        assert payload["attractions"] == [
            {
                "id": 1,
                "title": "灵山大佛",
                "scenic_area": "灵山胜境",
                "attraction_code": "LS-011",
            }
        ]
        assert payload["routes"] == [
            {
                "id": "route_001",
                "title": "历史文化路线",
                "duration_label": "6小时深度游",
                "tags": ["历史", "文化"],
            }
        ]
        assert session.scalar(select(QuickTopic).where(QuickTopic.key == "history")) is not None
    finally:
        session.close()
