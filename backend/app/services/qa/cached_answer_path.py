from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.services.qa.answer_styler import polish_answer


@dataclass(frozen=True)
class CachedAnswerResolution:
    answer: str | None
    sources: list[dict]
    stale: bool = False


async def resolve_cached_answer(
    *,
    cache,
    cache_key: str,
    allowed: bool,
    epoch: int | None,
    epoch_is_current: Callable[[], Awaitable[bool]],
    persona: str,
) -> CachedAnswerResolution | None:
    """Read, epoch-check, and style one already-approved shared cache hit."""
    if not allowed:
        return None

    cached = await cache.get(cache_key, epoch=epoch)
    if cached is None:
        return None
    if not await epoch_is_current():
        return CachedAnswerResolution(answer=None, sources=[], stale=True)
    return CachedAnswerResolution(
        answer=polish_answer(cached.answer, persona, cached.sources),
        sources=cached.sources,
    )
