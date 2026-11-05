from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.services.qa.stream_completion_effects import StreamCompletionEffects
from app.services.qa.stream_events import StreamEvent


class StreamAnswerCompletionFactory:
    """Bind one finalized generation to completion effects and SSE policy."""

    def __init__(
        self,
        *,
        completion,
        cache_writer: Callable[..., Awaitable[object]],
        persist_interaction: Callable[..., Awaitable[str | None]],
        blind_spot_tracker,
        request,
        normalized_query: str,
        sources: list[dict],
        expected_epoch: int | None,
        start: float,
        active_subject: str | None,
        followup_event: Callable[[], StreamEvent],
        done_event_builder: Callable[..., StreamEvent],
        faq_documents_present: bool,
        text_only: bool,
        epoch_is_current: Callable[[], Awaitable[bool]],
    ) -> None:
        self.completion = completion
        self.cache_writer = cache_writer
        self.persist_interaction = persist_interaction
        self.blind_spot_tracker = blind_spot_tracker
        self.request = request
        self.normalized_query = normalized_query
        self.sources = sources
        self.expected_epoch = expected_epoch
        self.start = start
        self.active_subject = active_subject
        self.followup_event = followup_event
        self.done_event_builder = done_event_builder
        self.faq_documents_present = faq_documents_present
        self.text_only = text_only
        self.epoch_is_current = epoch_is_current

    def build(self, outcome):
        stream_turn = outcome.stream_turn
        finalized = outcome.finalized
        terminal_policy = finalized.policy
        answer = finalized.answer
        stream_turn.answer_buffer.full_answer = answer
        effects = StreamCompletionEffects(
            cache_writer=self.cache_writer,
            persist_interaction=self.persist_interaction,
            blind_spot_tracker=self.blind_spot_tracker,
            request=self.request,
            normalized_query=self.normalized_query,
            answer=answer,
            sources=self.sources,
            hit_level=terminal_policy.hit_level,
            expected_epoch=self.expected_epoch,
            start=self.start,
            llm_usage=stream_turn.llm_usage,
            llm_finish_reason=stream_turn.llm_finish_reason,
            degraded=terminal_policy.degraded,
            provider=terminal_policy.provider,
            completion=terminal_policy.completion,
            active_subject=self.active_subject,
            followup_event=self.followup_event,
            done_event_builder=self.done_event_builder,
        )
        return self.completion.events(
            stream_turn=stream_turn,
            answer=answer,
            faq_text_sent=self.faq_documents_present,
            incomplete=terminal_policy.incomplete,
            faq_documents_present=self.faq_documents_present,
            text_only=self.text_only,
            streaming_requested=outcome.streaming_requested,
            epoch_is_current=self.epoch_is_current,
            cache_answer=effects.cache_answer if terminal_policy.should_cache else None,
            persist_answer=effects.persist_answer,
            followups_event=effects.followups_event,
            done_event=effects.done_event,
            after_audio=effects.after_audio,
        )
