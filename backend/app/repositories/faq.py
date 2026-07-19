from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq import FAQEntryRecord


class FAQRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[FAQEntryRecord]:
        stmt = select(FAQEntryRecord).order_by(FAQEntryRecord.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, faq_id: str) -> FAQEntryRecord | None:
        return await self.session.get(FAQEntryRecord, faq_id)

    async def upsert(
        self,
        *,
        faq_id: str,
        category: str,
        aliases_json: str,
        answer: str,
        sources_json: str,
    ) -> FAQEntryRecord:
        entry = await self.get(faq_id)
        if entry is None:
            entry = FAQEntryRecord(id=faq_id)
        entry.category = category
        entry.aliases_json = aliases_json
        entry.answer = answer
        entry.sources_json = sources_json
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def replace_all(
        self,
        entries: list[FAQEntryRecord],
        *,
        preserve_ids: set[str] | None = None,
    ) -> int:
        protected_ids = preserve_ids or set()
        delete_stmt = delete(FAQEntryRecord)
        if protected_ids:
            delete_stmt = delete_stmt.where(FAQEntryRecord.id.not_in(protected_ids))
        await self.session.execute(delete_stmt)
        self.session.add_all([entry for entry in entries if entry.id not in protected_ids])
        await self.session.flush()
        return len(entries)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(FAQEntryRecord.id)))
        return result.scalar_one_or_none() or 0
