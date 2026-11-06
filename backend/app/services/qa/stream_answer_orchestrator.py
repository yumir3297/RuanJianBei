from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from dataclasses import dataclass

from app.schemas.chat import ChatRequest
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.stream_answer_completion_factory import StreamAnswerCompletionFactory
from app.services.qa.stream_answer_generation_factory import StreamAnswerGenerationFactory
from app.services.qa.stream_answer_run import StreamAnswerRun
from app.services.qa.stream_events import StreamEvent
from app.services.rag.base import RetrievedDocument


@dataclass(frozen=True)
class StreamAnswerContext:
    """Bind the selected evidence and request policy for one generated answer."""

    request: ChatRequest
    documents: list[RetrievedDocument]
    audience: str | None
    memory: str | None
    confirmed_visual_title: str | None
    vision_context_present: bool
    faq_documents_present: bool
    cache_allowed: bool
    llm_hit_level: str
    fallback_hit_level: str
    faq_answer: str
    faq_sources: list[dict]
    normalized_query: str
    sources: list[dict]
    expected_epoch: int | None
    start: float
    cache_key: str
    resolved: ResolvedInteraction


class StreamAnswerOrchestrator:
    """Compose generation, terminal policy, and completion for one SSE answer."""

    def __init__(
        self,
        *,
        turn_factory,
        llm_provider_name: str,
        emotion_aware_query: Callable[[str], str],
        epoch_is_current: Callable[[int | None], Awaitable[bool]],
        completion,
        cache,
        persist_interaction: Callable[..., Awaitable[str | None]],
        blind_spot_tracker,
        followup_event_builder: Callable[[ResolvedInteraction], StreamEvent],
        done_event_builder: Callable[..., StreamEvent],
    ) -> None:
        self.turn_factory = turn_factory
        self.llm_provider_name = llm_provider_name
        self.emotion_aware_query = emotion_aware_query
        self.epoch_is_current = epoch_is_current
        self.completion = completion
        self.cache = cache
        self.persist_interaction = persist_interaction
        self.blind_spot_tracker = blind_spot_tracker
        self.followup_event_builder = followup_event_builder
        self.done_event_builder = done_event_builder

    async def events(self, context: StreamAnswerContext) -> AsyncIterator[StreamEvent]:
        epoch_is_current = lambda: self.epoch_is_current(context.expected_epoch)
        generation_run = StreamAnswerGenerationFactory(
            turn_factory=self.turn_factory,
            llm_provider_name=self.llm_provider_name,
            emotion_aware_query=self.emotion_aware_query,
            epoch_is_current=epoch_is_current,
        ).build(
            request=context.request,
            documents=context.documents,
            audience=context.audience,
            memory=context.memory,
            confirmed_visual_title=context.confirmed_visual_title,
            vision_context_present=context.vision_context_present,
            faq_documents_present=context.faq_documents_present,
            cache_allowed=context.cache_allowed,
            llm_hit_level=context.llm_hit_level,
            fallback_hit_level=context.fallback_hit_level,
            faq_answer=context.faq_answer,
            faq_sources=context.faq_sources,
        )
        completion_factory = StreamAnswerCompletionFactory(
            completion=self.completion,
            cache_writer=lambda answer, bound_sources, epoch: self.cache.set(
                context.cache_key, answer, bound_sources, epoch=epoch
            ),
            persist_interaction=self.persist_interaction,
            blind_spot_tracker=self.blind_spot_tracker,
            request=context.request,
            normalized_query=context.normalized_query,
            sources=context.sources,
            expected_epoch=context.expected_epoch,
            start=context.start,
            active_subject=context.resolved.active_subject,
            followup_event=lambda: self.followup_event_builder(context.resolved),
            done_event_builder=self.done_event_builder,
            faq_documents_present=context.faq_documents_present,
            text_only=context.request.text_only,
            epoch_is_current=epoch_is_current,
        )
        answer_run = StreamAnswerRun(
            generation_run=generation_run,
            completion_factory=completion_factory.build,
        )
        async with aclosing(answer_run.events()) as events:
            async for event in events:
                yield event
