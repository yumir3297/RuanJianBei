from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qa_cache import QACacheEntry


class QACacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, normalized_query: str) -> QACacheEntry | None:
        stmt = select(QACacheEntry).where(QACacheEntry.normalized_query == normalized_query)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set(self, normalized_query: str, answer: str, sources: list[dict], expires_at: datetime) -> QACacheEntry:
        entry = await self.get(normalized_query)
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
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def invalidate(self, normalized_query: str | None = None) -> None:
        if normalized_query is None:
            await self.session.execute(delete(QACacheEntry))
        else:
            stmt = delete(QACacheEntry).where(QACacheEntry.normalized_query == normalized_query)
            await self.session.execute(stmt)
        await self.session.commit()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(QACacheEntry.id)))
        return result.scalar_one_or_none() or 0
