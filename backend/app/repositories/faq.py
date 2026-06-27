from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.faq import FAQEntryRecord


class FAQRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[FAQEntryRecord]:
        stmt = select(FAQEntryRecord).order_by(FAQEntryRecord.id.asc())
        return list(self.session.scalars(stmt))

    def get(self, faq_id: str) -> FAQEntryRecord | None:
        return self.session.get(FAQEntryRecord, faq_id)

    def upsert(
        self,
        *,
        faq_id: str,
        category: str,
        aliases_json: str,
        answer: str,
        sources_json: str,
    ) -> FAQEntryRecord:
        entry = self.get(faq_id)
        if entry is None:
            entry = FAQEntryRecord(id=faq_id)
        entry.category = category
        entry.aliases_json = aliases_json
        entry.answer = answer
        entry.sources_json = sources_json
        self.session.add(entry)
        self.session.flush()
        return entry

    def replace_all(
        self,
        entries: list[FAQEntryRecord],
        *,
        preserve_ids: set[str] | None = None,
    ) -> int:
        protected_ids = preserve_ids or set()
        delete_stmt = delete(FAQEntryRecord)
        if protected_ids:
            delete_stmt = delete_stmt.where(FAQEntryRecord.id.not_in(protected_ids))
        self.session.execute(delete_stmt)
        self.session.add_all([entry for entry in entries if entry.id not in protected_ids])
        self.session.flush()
        return len(entries)

    def count(self) -> int:
        return self.session.scalar(select(func.count(FAQEntryRecord.id))) or 0
