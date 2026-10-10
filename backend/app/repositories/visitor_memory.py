from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor_memory import VisitorMemory

MAX_ATTRACTIONS = 20
MAX_TAGS = 12


def _load_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


class VisitorMemoryRepository:
    """按 (visitor_id, site_id) 聚合的跨会话记忆读写。

    visitor_id 只建普通索引不建唯一约束：同一游客在多景区场景下会各有一条记录，
    唯一性是"visitor_id + site_id"级别的，由这里的查询条件保证。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, visitor_id: str, *, site_id: str = "default") -> VisitorMemory | None:
        stmt = select(VisitorMemory).where(
            VisitorMemory.visitor_id == visitor_id,
            VisitorMemory.site_id == site_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def decode(memory: VisitorMemory) -> dict:
        return {
            "visitor_id": memory.visitor_id,
            "site_id": memory.site_id,
            "visit_count": int(memory.visit_count or 0),
            "visited_attractions": _load_list(memory.visited_attractions),
            "preference_tags": _load_list(memory.preference_tags),
            "narration_audience": memory.narration_audience or "adult",
            "first_seen_at": memory.first_seen_at,
            "last_seen_at": memory.last_seen_at,
        }

    async def record_visit(
        self,
        *,
        visitor_id: str,
        session_id: str = "",
        site_id: str = "default",
        attraction_title: str | None = None,
        interests: list[str] | None = None,
        narration_audience: str = "adult",
    ) -> VisitorMemory:
        memory = await self.get(visitor_id, site_id=site_id)
        if memory is None:
            memory = VisitorMemory(
                visitor_id=visitor_id,
                site_id=site_id,
                visited_attractions="[]",
                preference_tags="[]",
                narration_audience=narration_audience or "adult",
                visit_count=0,
                last_session_id="",
            )
            attractions: list[str] = []
            tags: list[str] = []
        else:
            attractions = _load_list(memory.visited_attractions)
            tags = _load_list(memory.preference_tags)

        if attraction_title and attraction_title.strip() and attraction_title not in attractions:
            attractions.append(attraction_title.strip())
        for tag in interests or []:
            if tag and tag not in tags:
                tags.append(tag)

        # 只有换会话才算一次新到访，避免同一会话内多轮灌水
        if session_id and session_id != (memory.last_session_id or ""):
            memory.visit_count = int(memory.visit_count or 0) + 1
            memory.last_session_id = session_id

        memory.visited_attractions = json.dumps(attractions[-MAX_ATTRACTIONS:], ensure_ascii=False)
        memory.preference_tags = json.dumps(tags[-MAX_TAGS:], ensure_ascii=False)
        if narration_audience:
            memory.narration_audience = narration_audience
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def delete(self, visitor_id: str, *, site_id: str = "default") -> int:
        result = await self.session.execute(
            delete(VisitorMemory).where(
                VisitorMemory.visitor_id == visitor_id,
                VisitorMemory.site_id == site_id,
            )
        )
        await self.session.commit()
        return int(result.rowcount or 0)
