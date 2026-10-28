from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge import KnowledgeEntry


class KnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .join(KnowledgeEntry, KnowledgeEntry.id == KnowledgeChunk.source_entry_id)
            .where(
                KnowledgeChunk.revision_id.is_not(None),
                KnowledgeEntry.published_revision_id == KnowledgeChunk.revision_id,
                KnowledgeEntry.withdrawn_at.is_(None),
            )
            .order_by(KnowledgeChunk.source_entry_id.asc(), KnowledgeChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_all(self, chunks: list[KnowledgeChunk]) -> int:
        await self.session.execute(delete(KnowledgeChunk))
        self.session.add_all(chunks)
        await self.session.flush()
        return len(chunks)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(KnowledgeChunk.chunk_id)))
        return result.scalar_one_or_none() or 0
