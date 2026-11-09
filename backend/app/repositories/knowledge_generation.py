from __future__ import annotations

from app.models.knowledge_generation import KnowledgeGeneration
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession


class KnowledgeGenerationRepository:
    SINGLETON_ID = 1

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> KnowledgeGeneration:
        state = await self.session.get(KnowledgeGeneration, self.SINGLETON_ID)
        if state is None:
            state = KnowledgeGeneration(id=self.SINGLETON_ID, generation=1, indexed_generation=0)
            self.session.add(state)
            await self.session.flush()
        return state

    async def bump(self, *, commit: bool = False) -> int:
        state = await self.get()
        await self.session.execute(
            update(KnowledgeGeneration)
            .where(KnowledgeGeneration.id == self.SINGLETON_ID)
            .values(generation=KnowledgeGeneration.generation + 1)
        )
        await self.session.flush()
        await self.session.refresh(state)
        if commit:
            await self.session.commit()
        return state.generation

    async def mark_indexed(self, generation: int, *, commit: bool = False) -> bool:
        result = await self.session.execute(
            update(KnowledgeGeneration)
            .where(
                KnowledgeGeneration.id == self.SINGLETON_ID,
                KnowledgeGeneration.generation == generation,
            )
            .values(indexed_generation=generation)
        )
        if result.rowcount != 1:
            return False
        await self.session.flush()
        if commit:
            await self.session.commit()
        return True
