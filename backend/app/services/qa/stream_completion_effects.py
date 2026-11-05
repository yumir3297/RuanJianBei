from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable

from app.services.qa.stream_events import StreamEvent

logger = logging.getLogger(__name__)


class StreamCompletionEffects:
    """Bind per-request persistence, caching, fallback recording, and terminal metadata."""

    def __init__(
        self,
        *,
        cache_writer: Callable[..., object],
        persist_interaction: Callable[..., object],
        blind_spot_tracker,
        request,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        expected_epoch: int | None,
        start: float,
        llm_usage,
        llm_finish_reason: str | None,
        degraded: bool,
        provider: str,
        completion: str,
        active_subject: str | None,
        followup_event: Callable[[], StreamEvent],
        done_event_builder: Callable[..., StreamEvent],
    ) -> None:
        self.cache_writer = cache_writer
        self.persist_interaction = persist_interaction
        self.blind_spot_tracker = blind_spot_tracker
        self.request = request
        self.normalized_query = normalized_query
        self.answer = answer
        self.sources = sources
        self.hit_level = hit_level
        self.expected_epoch = expected_epoch
        self.start = start
        self.llm_usage = llm_usage
        self.llm_finish_reason = llm_finish_reason
        self.degraded = degraded
        self.provider = provider
        self.completion = completion
        self.active_subject = active_subject
        self.followup_event = followup_event
        self.done_event_builder = done_event_builder
        self.latency_ms = 0

    async def cache_answer(self) -> None:
        await self.cache_writer(self.answer, self.sources, self.expected_epoch)

    async def persist_answer(self) -> str | None:
        self.latency_ms = int((perf_counter() - self.start) * 1000)
        return await self.persist_interaction(
            session_id=self.request.session_id,
            raw_query=self.request.query,
            normalized_query=self.normalized_query,
            answer=self.answer,
            sources=self.sources,
            hit_level=self.hit_level,
            latency_ms=self.latency_ms,
            request=self.request,
            active_subject=self.active_subject,
        )

    async def after_audio(self) -> None:
        if not self.degraded or self.blind_spot_tracker is None:
            return
        try:
            await self.blind_spot_tracker.record(
                raw_query=self.request.query,
                normalized_query=self.normalized_query,
                category="llm_fallback",
            )
            logger.info("Blind spot recorded (LLM degraded)")
        except Exception:
            logger.exception("Knowledge blind spot recording failed")

    def followups_event(self) -> StreamEvent:
        return self.followup_event()

    def done_event(self, chat_log_id: str | None) -> StreamEvent:
        usage = self.llm_usage
        logger.info(
            "LLM completed: finish_reason=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s cached_tokens=%s",
            self.llm_finish_reason,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
            usage.cached_tokens,
        )
        return self.done_event_builder(
            chat_log_id=chat_log_id,
            hit_level=self.hit_level,
            total_ms=self.latency_ms,
            degraded=self.degraded,
            provider=self.provider,
            completion=self.completion,
        )
