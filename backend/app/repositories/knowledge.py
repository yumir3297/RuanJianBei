from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeEntry
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[KnowledgeEntry]:
        stmt: Select[tuple[KnowledgeEntry]] = select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, knowledge_id: int) -> KnowledgeEntry | None:
        return await self.session.get(KnowledgeEntry, knowledge_id)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(KnowledgeEntry.id)))
        return result.scalar_one_or_none() or 0

    async def list_by_sources(self, sources: list[str]) -> list[KnowledgeEntry]:
        if not sources:
            return []
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.source.in_(sources))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_category(self, category: str) -> list[KnowledgeEntry]:
        stmt = (
            select(KnowledgeEntry)
            .where(KnowledgeEntry.category == category)
            .order_by(KnowledgeEntry.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_attraction(self, knowledge_id: int) -> KnowledgeEntry | None:
        entry = await self.get(knowledge_id)
        if entry is None or entry.category != "景点信息":
            return None
        return entry

    async def find_route_overview(self, route_title: str) -> KnowledgeEntry | None:
        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.category == "游览路线",
                KnowledgeEntry.title.ilike(f"{route_title}%"),
            )
            .order_by(KnowledgeEntry.id.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        limit: int = 10,
        *,
        knowledge_id: int | None = None,
        category: str | None = None,
    ) -> list[KnowledgeEntry]:
        if knowledge_id is not None:
            entry = await self.get(knowledge_id)
            if entry is None or (category is not None and entry.category != category):
                return []
            return [entry]

        pattern = f"%{query}%"
        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.title.ilike(pattern)
                | KnowledgeEntry.content.ilike(pattern)
                | KnowledgeEntry.aliases.ilike(pattern)
            )
            .limit(limit)
        )
        if category is not None:
            stmt = stmt.where(KnowledgeEntry.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, payload: KnowledgeCreate) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            title=payload.title,
            category=payload.category,
            content=payload.content,
            source=payload.source,
            aliases="|".join(payload.aliases),
            metadata_json=payload.metadata_json,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def update(self, entry: KnowledgeEntry, payload: KnowledgeUpdate) -> KnowledgeEntry:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key == "aliases" and value is not None:
                setattr(entry, key, "|".join(value))
            else:
                setattr(entry, key, value)
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def delete(self, entry: KnowledgeEntry) -> None:
        self.session.delete(entry)
        await self.session.commit()
