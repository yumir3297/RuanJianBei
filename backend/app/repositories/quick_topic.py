from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quick_topic import QuickTopic


class QuickTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_enabled(self) -> list[QuickTopic]:
        stmt = (
            select(QuickTopic)
            .where(QuickTopic.is_enabled.is_(True))
            .order_by(QuickTopic.sort_order.asc(), QuickTopic.key.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_enabled(self, topic_key: str) -> QuickTopic | None:
        stmt = select(QuickTopic).where(
            QuickTopic.key == topic_key,
            QuickTopic.is_enabled.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def seed_missing(self, topics: Iterable[dict]) -> int:
        result = await self.session.execute(select(QuickTopic.key))
        existing_keys = set(result.scalars())
        missing = [QuickTopic(**topic) for topic in topics if topic["key"] not in existing_keys]
        if not missing:
            return 0

        self.session.add_all(missing)
        await self.session.commit()
        return len(missing)
