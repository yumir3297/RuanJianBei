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

    async def get(self, chunk_id: str) -> KnowledgeChunk | None:
        return await self.session.get(KnowledgeChunk, chunk_id)

    async def replace_unpublished(self, chunks: list[KnowledgeChunk]) -> int:
        if any(chunk.revision_id is not None for chunk in chunks):
            raise ValueError("仅可刷新尚未发布的知识分块")
        await self.session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.revision_id.is_(None)))
        self.session.add_all(chunks)
        await self.session.flush()
        return len(chunks)

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(KnowledgeChunk.chunk_id)))
        return result.scalar_one_or_none() or 0
