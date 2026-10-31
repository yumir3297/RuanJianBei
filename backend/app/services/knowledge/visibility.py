from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_workspace import KnowledgeState


class VisibilityService:
    """Checks vector/cache results against the durable published knowledge state."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def read_epoch(self) -> int:
        result = await self.session.execute(select(KnowledgeState.epoch).where(KnowledgeState.id == 1))
        epoch = result.scalar_one_or_none()
        return epoch if epoch is not None else 1

    async def filter_published_chunks(self, references: list[tuple[str, int, str]]) -> set[tuple[str, int, str]]:
        return set(await self.get_published_chunks(references))

    async def get_published_chunks(self, references: list[tuple[str, int, str]]) -> dict[tuple[str, int, str], KnowledgeChunk]:
        if not references:
            return {}
        result = await self.session.scalars(
            select(KnowledgeChunk)
            .join(KnowledgeEntry, KnowledgeEntry.id == KnowledgeChunk.source_entry_id)
            .where(KnowledgeChunk.chunk_id.in_({item[0] for item in references}),
                   KnowledgeEntry.withdrawn_at.is_(None),
                   KnowledgeChunk.revision_id == KnowledgeEntry.published_revision_id,
                   KnowledgeChunk.revision_id.is_not(None))
        )
        wanted = set(references)
        return {(chunk.chunk_id, int(chunk.source_entry_id), chunk.revision_id): chunk
                for chunk in result.all()
                if (chunk.chunk_id, int(chunk.source_entry_id), chunk.revision_id) in wanted}

    async def filter_published(self, references: list[tuple[int, str]]) -> set[tuple[int, str]]:
        if not references:
            return set()
        entry_ids = {entry_id for entry_id, _ in references}
        result = await self.session.execute(
            select(KnowledgeEntry.id, KnowledgeEntry.published_revision_id)
            .where(
                KnowledgeEntry.id.in_(entry_ids),
                KnowledgeEntry.withdrawn_at.is_(None),
                KnowledgeEntry.published_revision_id.is_not(None),
            )
        )
        current = {(int(entry_id), revision_id) for entry_id, revision_id in result.all()}
        return {reference for reference in references if reference in current}
