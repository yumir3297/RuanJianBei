from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import engine
from app.db.session import SessionLocal
from app.models.avatar_config import AvatarConfig
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.schemas.knowledge import KnowledgeCreate


DEFAULT_AVATAR_CONFIGS = (
    {
        "name": "僧袍法师",
        "model_path": "preset:monk",
        "preview_url": "",
        "voice_type": "deep-male",
        "is_active": False,
    },
    {
        "name": "汉服导游",
        "model_path": "preset:hanfu",
        "preview_url": "",
        "voice_type": "gentle-female",
        "is_active": True,
    },
    {
        "name": "现代导游",
        "model_path": "preset:modern",
        "preview_url": "",
        "voice_type": "deep-male",
        "is_active": False,
    },
)


DEFAULT_QUICK_TOPICS = (
    {
        "key": "attractions",
        "label": "景点介绍",
        "category": "knowledge",
        "icon": "landmark",
        "sort_order": 10,
        "is_enabled": True,
    },
    {
        "key": "history",
        "label": "历史文化",
        "category": "knowledge",
        "icon": "scroll-text",
        "sort_order": 20,
        "is_enabled": True,
    },
    {
        "key": "architecture",
        "label": "建筑艺术",
        "category": "knowledge",
        "icon": "building",
        "sort_order": 30,
        "is_enabled": True,
    },
    {
        "key": "blessing",
        "label": "祈福体验",
        "category": "knowledge",
        "icon": "sparkles",
        "sort_order": 40,
        "is_enabled": True,
    },
    {
        "key": "routes",
        "label": "路线推荐",
        "category": "recommend",
        "icon": "route",
        "sort_order": 50,
        "is_enabled": True,
    },
    {
        "key": "family",
        "label": "亲子游玩",
        "category": "recommend",
        "icon": "family",
        "sort_order": 60,
        "is_enabled": True,
    },
    {
        "key": "practical",
        "label": "实用信息",
        "category": "faq",
        "icon": "ticket",
        "sort_order": 70,
        "is_enabled": True,
    },
    {
        "key": "dining",
        "label": "餐饮服务",
        "category": "faq",
        "icon": "utensils",
        "sort_order": 80,
        "is_enabled": True,
    },
)


def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("knowledge_entries"):
        return

    column_names = {column["name"] for column in inspector.get_columns("knowledge_entries")}
    if "metadata_json" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE knowledge_entries ADD COLUMN metadata_json TEXT"))


def seed_quick_topics(session) -> int:
    return QuickTopicRepository(session).seed_missing(DEFAULT_QUICK_TOPICS)


def seed_avatar_configs(session) -> int:
    existing = session.query(AvatarConfig).count()
    if existing > 0:
        return 0
    for item in DEFAULT_AVATAR_CONFIGS:
        session.add(AvatarConfig(**item))
    session.commit()
    return len(DEFAULT_AVATAR_CONFIGS)


def bootstrap_quick_topics() -> None:
    session = SessionLocal()
    try:
        seed_quick_topics(session)
    finally:
        session.close()


def bootstrap_avatar_configs() -> None:
    session = SessionLocal()
    try:
        seed_avatar_configs(session)
    finally:
        session.close()


def bootstrap_sample_data() -> None:
    settings = get_settings()
    if not settings.enable_sample_data:
        return
    if settings.processed_data_available:
        return

    session = SessionLocal()
    try:
        repository = KnowledgeRepository(session)
        if repository.list_all():
            return

        samples = [
            KnowledgeCreate(
                title="灵山大佛",
                category="景点信息",
                content="灵山大佛是景区核心景点之一，常见问答包括高度、文化意义和游览顺序。",
                source=settings.default_knowledge_source,
                aliases=["大佛", "灵山大佛"],
            ),
            KnowledgeCreate(
                title="五印坛城",
                category="文化建筑",
                content="五印坛城常与藏文化展示、坛城建筑结构和参观路线问题相关。",
                source=settings.default_knowledge_source,
                aliases=["坛城", "五印坛城"],
            ),
        ]
        for item in samples:
            repository.create(item)
    finally:
        session.close()
