from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior_summary import BehaviorSummary


class BehaviorSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_all(self, summaries: list[BehaviorSummary]) -> int:
        await self.session.execute(delete(BehaviorSummary))
        self.session.add_all(summaries)
        await self.session.flush()
        return len(summaries)

    async def get_latest(self) -> BehaviorSummary | None:
        stmt = select(BehaviorSummary).order_by(BehaviorSummary.updated_at.desc(), BehaviorSummary.id.desc())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(BehaviorSummary.id)))
        return result.scalar_one_or_none() or 0
