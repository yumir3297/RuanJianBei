from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState


class KnowledgeWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_revision(self, revision_id: str) -> KnowledgeRevision | None:
        return await self.session.get(KnowledgeRevision, revision_id)

    async def list_revisions(self, knowledge_entry_id: int) -> list[KnowledgeRevision]:
        result = await self.session.execute(
            select(KnowledgeRevision)
            .where(KnowledgeRevision.knowledge_entry_id == knowledge_entry_id)
            .order_by(KnowledgeRevision.created_at.desc(), KnowledgeRevision.id.desc())
        )
        return list(result.scalars().all())

    async def get_epoch(self) -> int:
        state = await self.session.get(KnowledgeState, 1)
        return state.epoch if state is not None else 1
