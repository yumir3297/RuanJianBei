from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.avatar_config import AvatarConfig
from app.models.knowledge import KnowledgeEntry
from app.models.quick_topic import QuickTopic
from app.models.visitor_feedback import VisitorFeedback
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


async def seed_quick_topics(session: AsyncSession) -> int:
    result = await session.execute(select(QuickTopic.key))
    existing_keys = set(result.scalars().all())
    missing = [QuickTopic(**topic) for topic in DEFAULT_QUICK_TOPICS if topic["key"] not in existing_keys]
    if not missing:
        return 0
    session.add_all(missing)
    await session.commit()
    return len(missing)


async def seed_avatar_configs(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(AvatarConfig.id)))
    existing = result.scalar_one() or 0
    if existing > 0:
        return 0
    for item in DEFAULT_AVATAR_CONFIGS:
        session.add(AvatarConfig(**item))
    await session.commit()
    return len(DEFAULT_AVATAR_CONFIGS)


async def bootstrap_quick_topics() -> None:
    async with AsyncSessionLocal() as session:
        await seed_quick_topics(session)


async def bootstrap_avatar_configs() -> None:
    async with AsyncSessionLocal() as session:
        await seed_avatar_configs(session)


async def bootstrap_sample_data() -> None:
    settings = get_settings()
    if not settings.enable_sample_data:
        return
    if settings.processed_data_available:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(KnowledgeEntry).limit(1))
        if result.scalars().first():
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
            entry = KnowledgeEntry(
                title=item.title,
                category=item.category,
                content=item.content,
                source=item.source,
                aliases="|".join(item.aliases),
                metadata_json=item.metadata_json,
            )
            session.add(entry)
        await session.commit()


async def bootstrap_experience_demo_feedback() -> None:
    """Seed database records for the first judge-facing report, never frontend constants."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count()).select_from(VisitorFeedback).where(VisitorFeedback.is_demo.is_(True))
        )
        if result.scalar_one():
            return
        now = datetime.now()
        samples = [
            ("positive", None, -6), ("positive", None, -5), ("negative", "detail", -5),
            ("positive", None, -4), ("positive", None, -4), ("negative", "recommendation", -3),
            ("positive", None, -3), ("positive", None, -2), ("negative", "accuracy", -2),
            ("positive", None, -1), ("positive", None, -1), ("positive", None, 0),
        ]
        for index, (rating, reason, offset) in enumerate(samples, start=1):
            session.add(
                VisitorFeedback(
                    session_id=f"demo-judge-{index:02d}",
                    rating=rating,
                    reason_code=reason,
                    is_demo=True,
                    created_at=now + timedelta(days=offset),
                )
            )
        await session.commit()
