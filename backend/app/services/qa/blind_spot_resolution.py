from __future__ import annotations

import json

from app.core.exceptions import NotFoundError
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.repositories.faq import FAQRepository
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.schemas.blind_spot import ResolveBlindSpotWithFAQRequest


class BlindSpotResolutionService:
    def __init__(
        self,
        blind_spot_repository: KnowledgeBlindSpotRepository,
        faq_repository: FAQRepository,
    ) -> None:
        self.blind_spot_repository = blind_spot_repository
        self.faq_repository = faq_repository
        self.session = blind_spot_repository.session

    async def resolve_with_faq(
        self,
        blind_spot_id: int,
        payload: ResolveBlindSpotWithFAQRequest,
    ) -> KnowledgeBlindSpot:
        blind_spot = await self.blind_spot_repository.get(blind_spot_id)
        if blind_spot is None:
            raise NotFoundError("Knowledge blind spot not found.")

        aliases = self._merge_aliases(
            payload.aliases,
            self.blind_spot_repository.load_samples(blind_spot.raw_query_samples_json),
        )
        await self.faq_repository.upsert(
            faq_id=payload.faq_id,
            category=payload.category,
            aliases_json=json.dumps(aliases, ensure_ascii=False),
            answer=payload.answer,
            sources_json=json.dumps(payload.sources, ensure_ascii=False),
        )
        await self.blind_spot_repository.mark_resolved_with_faq(
            blind_spot,
            faq_id=payload.faq_id,
            category=payload.category,
        )
        await self.session.commit()
        await self.session.refresh(blind_spot)
        return blind_spot

    @staticmethod
    def _merge_aliases(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for value in group:
                stripped = value.strip()
                key = "".join(stripped.lower().split())
                if stripped and key not in seen:
                    seen.add(key)
                    merged.append(stripped)
        return merged
