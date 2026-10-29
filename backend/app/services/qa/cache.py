from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.repositories.qa_cache import QACacheRepository


@dataclass(slots=True)
class CachedAnswer:
    answer: str
    sources: list[dict]
    expires_at: datetime


class QACache:
    def __init__(self, repository: QACacheRepository, ttl_seconds: int, max_items: int = 128) -> None:
        self.repository = repository
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.memory_cache: OrderedDict[str, CachedAnswer] = OrderedDict()

    async def get(self, normalized_query: str, *, epoch: int | None = None) -> CachedAnswer | None:
        cache_key = self._key(normalized_query, epoch)
        cached = self.memory_cache.get(cache_key)
        if cached and cached.expires_at > datetime.now(UTC):
            self.memory_cache.move_to_end(cache_key)
            return cached

        entry = await self.repository.get(cache_key)
        if entry is None:
            return None

        expires_at = entry.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            await self.repository.invalidate(cache_key)
            return None

        restored = CachedAnswer(
            answer=entry.answer,
            sources=json.loads(entry.sources),
            expires_at=expires_at,
        )
        self._remember(cache_key, restored)
        return restored

    async def set(
        self, normalized_query: str, answer: str, sources: list[dict], ttl: int | None = None,
        *, epoch: int | None = None,
    ) -> CachedAnswer:
        cache_key = self._key(normalized_query, epoch)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl or self.ttl_seconds)
        cached = CachedAnswer(answer=answer, sources=sources, expires_at=expires_at)
        self._remember(cache_key, cached)
        await self.repository.set(cache_key, answer, sources, expires_at)
        return cached

    async def invalidate(self, normalized_query: str | None = None) -> None:
        if normalized_query is None:
            self.memory_cache.clear()
        else:
            self.memory_cache.pop(normalized_query, None)
        await self.repository.invalidate(normalized_query)

    def _remember(self, normalized_query: str, cached: CachedAnswer) -> None:
        self.memory_cache[normalized_query] = cached
        self.memory_cache.move_to_end(normalized_query)
        while len(self.memory_cache) > self.max_items:
            self.memory_cache.popitem(last=False)

    @staticmethod
    def _key(normalized_query: str, epoch: int | None) -> str:
        if epoch is None:
            return normalized_query
        return f"e{epoch}:{normalized_query}"

