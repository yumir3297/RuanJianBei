from __future__ import annotations

from hashlib import sha256

from sqlalchemy.exc import IntegrityError

from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository


class BlindSpotTracker:
    def __init__(
        self,
        repository: KnowledgeBlindSpotRepository,
        *,
        sample_limit: int = 5,
    ) -> None:
        self.repository = repository
        self.sample_limit = sample_limit

    async def record(
        self,
        *,
        raw_query: str,
        normalized_query: str,
        category: str = "unknown",
    ) -> KnowledgeBlindSpot:
        key = self._bounded_key(normalized_query)
        try:
            entry = await self.repository.record(
                normalized_query=key,
                raw_query=raw_query.strip(),
                category=category,
                sample_limit=self.sample_limit,
            )
            await self.repository.session.commit()
        except IntegrityError:
            await self.repository.session.rollback()
            entry = await self.repository.record(
                normalized_query=key,
                raw_query=raw_query.strip(),
                category=category,
                sample_limit=self.sample_limit,
            )
            await self.repository.session.commit()
        await self.repository.session.refresh(entry)
        return entry

    @staticmethod
    def _bounded_key(normalized_query: str) -> str:
        normalized = normalized_query.strip()
        if len(normalized) <= 500:
            return normalized
        digest = sha256(normalized.encode("utf-8")).hexdigest()
        return f"{normalized[:434]}:{digest}"
