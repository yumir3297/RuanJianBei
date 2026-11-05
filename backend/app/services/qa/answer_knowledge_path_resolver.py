from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.services.qa.answer_fast_paths import FAQPathDecision, shared_cache_allowed
from app.services.qa.cached_answer_path import CachedAnswerResolution, resolve_cached_answer
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.faq_path_resolver import resolve_faq_path_for_request


@dataclass(frozen=True, slots=True)
class AnswerKnowledgePathResolution:
    faq_path: FAQPathDecision | None
    cache_allowed: bool | None
    cached_answer: CachedAnswerResolution | None


class AnswerKnowledgePathResolver:
    """Preserve FAQ-before-cache routing and shared-cache eligibility gates."""

    def __init__(self, *, faq_matcher: FAQMatcher, cache) -> None:
        self.faq_matcher = faq_matcher
        self.cache = cache

    async def resolve(
        self,
        *,
        normalized_query: str,
        audience: str | None,
        persona: str,
        vision_present: bool,
        scoped_attraction: bool,
        memory_prompt: str | None,
        neutral: bool,
        cache_key: str,
        epoch: int | None,
        epoch_is_current: Callable[[], Awaitable[bool]],
    ) -> AnswerKnowledgePathResolution:
        faq_path = resolve_faq_path_for_request(
            self.faq_matcher,
            normalized_query,
            audience=audience,
            persona=persona,
            vision_present=vision_present,
            scoped_attraction=scoped_attraction,
        )
        if faq_path is not None and faq_path.answer is not None:
            return AnswerKnowledgePathResolution(
                faq_path=faq_path,
                cache_allowed=None,
                cached_answer=None,
            )

        cache_allowed = shared_cache_allowed(
            vision_present=vision_present,
            memory_prompt=memory_prompt,
            neutral=neutral,
        )
        cached_answer = await resolve_cached_answer(
            cache=self.cache,
            cache_key=cache_key,
            allowed=cache_allowed,
            epoch=epoch,
            epoch_is_current=epoch_is_current,
            persona=persona,
        )
        return AnswerKnowledgePathResolution(
            faq_path=faq_path,
            cache_allowed=cache_allowed,
            cached_answer=cached_answer,
        )
