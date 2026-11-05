from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing

from app.schemas.chat import ChatRequest
from app.services.emotion import EmotionResponsePolicy, apply_answer_prefix
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.stream_events import StreamEvent


class FastPathAnswerFactory:
    """Bind one fast-path answer to its request-scoped effects and SSE policy."""

    def __init__(
        self,
        *,
        coordinator,
        citation_binder: Callable[[str, list[dict]], str],
        persist_interaction: Callable[..., Awaitable[int | None]],
        done_event_builder: Callable[..., StreamEvent],
        followup_event_builder: Callable[[ResolvedInteraction], StreamEvent],
    ) -> None:
        self.coordinator = coordinator
        self.citation_binder = citation_binder
        self.persist_interaction = persist_interaction
        self.done_event_builder = done_event_builder
        self.followup_event_builder = followup_event_builder

    async def events(
        self,
        *,
        request: ChatRequest,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        start: float,
        resolved: ResolvedInteraction,
        response_policy: EmotionResponsePolicy,
        expected_epoch: int | None,
    ) -> AsyncIterator[StreamEvent]:
        def prepare_answer(value: str, bound_sources: list[dict]) -> str:
            styled = apply_answer_prefix(value, response_policy)
            return self.citation_binder(styled, bound_sources)

        async def persist_answer(value: str, latency_ms: int) -> int | None:
            return await self.persist_interaction(
                session_id=request.session_id,
                raw_query=request.query,
                normalized_query=normalized_query,
                answer=value,
                sources=sources,
                hit_level=hit_level,
                latency_ms=latency_ms,
                request=request,
                active_subject=resolved.active_subject,
            )

        def done_event(chat_log_id: int | None, latency_ms: int) -> StreamEvent:
            return self.done_event_builder(
                chat_log_id=chat_log_id,
                hit_level=hit_level,
                total_ms=latency_ms,
                degraded=hit_level in {
                    "rag_insufficient", "rag_llm_fallback", "schedule_unverified", "ticket_unverified"
                },
                provider=(
                    "local"
                    if hit_level.startswith("faq_")
                    or hit_level in {
                        "cache", "schedule_unverified", "ticket_unverified", "static_route",
                        "route_clarification",
                    }
                    else "rag"
                ),
            )

        answer_events = self.coordinator.events(
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            text_only=request.text_only,
            expected_epoch=expected_epoch,
            start=start,
            prepare_answer=prepare_answer,
            persist_answer=persist_answer,
            followups_event=lambda: self.followup_event_builder(resolved),
            done_event=done_event,
        )
        async with aclosing(answer_events) as events:
            async for event in events:
                yield event
