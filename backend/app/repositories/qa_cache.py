from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.qa_cache import QACacheEntry


class QACacheRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, normalized_query: str) -> QACacheEntry | None:
        stmt = select(QACacheEntry).where(QACacheEntry.normalized_query == normalized_query)
        return self.session.scalar(stmt)

    def set(self, normalized_query: str, answer: str, sources: list[dict], expires_at: datetime) -> QACacheEntry:
        entry = self.get(normalized_query)
        if entry is None:
            entry = QACacheEntry(
                normalized_query=normalized_query,
                answer=answer,
                sources=json.dumps(sources, ensure_ascii=False),
                expires_at=expires_at,
            )
        else:
            entry.answer = answer
            entry.sources = json.dumps(sources, ensure_ascii=False)
            entry.expires_at = expires_at
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def invalidate(self, normalized_query: str | None = None) -> None:
        if normalized_query is None:
            self.session.execute(delete(QACacheEntry))
        else:
            stmt = delete(QACacheEntry).where(QACacheEntry.normalized_query == normalized_query)
            self.session.execute(stmt)
        self.session.commit()

    def count(self) -> int:
        return self.session.scalar(select(func.count(QACacheEntry.id))) or 0

