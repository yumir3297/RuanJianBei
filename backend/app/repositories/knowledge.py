from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeEntry
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[KnowledgeEntry]:
        stmt: Select[tuple[KnowledgeEntry]] = select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc())
        return list(self.session.scalars(stmt))

    def get(self, knowledge_id: int) -> KnowledgeEntry | None:
        return self.session.get(KnowledgeEntry, knowledge_id)

    def count(self) -> int:
        return self.session.scalar(select(func.count(KnowledgeEntry.id))) or 0

    def list_by_sources(self, sources: list[str]) -> list[KnowledgeEntry]:
        if not sources:
            return []
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.source.in_(sources))
        return list(self.session.scalars(stmt))

    def list_by_category(self, category: str) -> list[KnowledgeEntry]:
        stmt = (
            select(KnowledgeEntry)
            .where(KnowledgeEntry.category == category)
            .order_by(KnowledgeEntry.id.asc())
        )
        return list(self.session.scalars(stmt))

    def get_attraction(self, knowledge_id: int) -> KnowledgeEntry | None:
        entry = self.get(knowledge_id)
        if entry is None or entry.category != "景点信息":
            return None
        return entry

    def find_route_overview(self, route_title: str) -> KnowledgeEntry | None:
        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.category == "游览路线",
                KnowledgeEntry.title.ilike(f"{route_title}%"),
            )
            .order_by(KnowledgeEntry.id.asc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def search(
        self,
        query: str,
        limit: int = 10,
        *,
        knowledge_id: int | None = None,
        category: str | None = None,
    ) -> list[KnowledgeEntry]:
        if knowledge_id is not None:
            entry = self.get(knowledge_id)
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
        return list(self.session.scalars(stmt))

    def create(self, payload: KnowledgeCreate) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            title=payload.title,
            category=payload.category,
            content=payload.content,
            source=payload.source,
            aliases="|".join(payload.aliases),
            metadata_json=payload.metadata_json,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def update(self, entry: KnowledgeEntry, payload: KnowledgeUpdate) -> KnowledgeEntry:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key == "aliases" and value is not None:
                setattr(entry, key, "|".join(value))
            else:
                setattr(entry, key, value)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def delete(self, entry: KnowledgeEntry) -> None:
        self.session.delete(entry)
        self.session.commit()
