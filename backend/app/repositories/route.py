from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import RouteTemplate


class RouteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[RouteTemplate]:
        stmt = select(RouteTemplate).order_by(RouteTemplate.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, route_id: str) -> RouteTemplate | None:
        return await self.session.get(RouteTemplate, route_id)

    async def replace_all(self, routes: list[RouteTemplate]) -> int:
        await self.session.execute(delete(RouteTemplate))
        self.session.add_all(routes)
        await self.session.flush()
        return len(routes)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(RouteTemplate.id)))
        return result.scalar_one_or_none() or 0
