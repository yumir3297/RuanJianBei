from __future__ import annotations

import asyncio
import json
import logging
from contextlib import aclosing
from contextvars import ContextVar, Token
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from app.repositories.chat_log import ChatLogRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.repositories.visitor_memory import VisitorMemoryRepository
from app.schemas.chat import ChatRequest
from app.services.avatar.base import BaseAvatarService
from app.services.llm.base import BaseLLMService
from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.emotion import (
    EmotionLabel,
    EmotionResponsePolicy,
    EmotionSignal,
    FusedEmotion,
    MultimodalEmotionFusion,
    TextEmotionAnalyzer,
    apply_answer_prefix,
    audio_emotion_signal,
    response_policy_for,
)
from app.services.memory.profile import build_memory_prompt
from app.services.qa.cache import QACache
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.answer_fast_paths import (
    resolve_ticket_answer,
    resolve_unverified_schedule_answer,
    shared_cache_allowed,
)
from app.services.qa.faq_path_resolver import resolve_faq_path_for_request
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import (
    GuidedSelectionResolver,
    ResolvedInteraction,
    build_selection_cache_key,
)
from app.services.qa.intent_router import IntentRouter
from app.services.qa.route_constraints import explicit_route_hours as _explicit_route_hours
from app.services.qa.request_profile import (
    extract_interests as _extract_interests,
    infer_audience_type as _infer_audience_type,
    resolve_narration_audience as _resolve_narration_audience,
)
from app.services.qa.request_query_context import resolve_request_query_context
from app.services.qa.route_fast_path import StaticRouteAnswerBuilder
from app.services.qa.speech_event_adapter import (
    build_audio_event as build_speech_audio_event,
    build_viseme_timeline as build_speech_viseme_timeline,
    handle_streaming_tts_event as adapt_streaming_tts_event,
    words_to_viseme_timeline as build_words_viseme_timeline,
)
from app.services.qa.stream_events import StreamEvent
from app.services.qa.final_answer_speech_emitter import FinalAnswerSpeechEmitter
from app.services.qa.fast_path_answer_coordinator import FastPathAnswerCoordinator
from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_completion import StreamCompletionCoordinator
from app.services.qa.stream_answer_completion_factory import StreamAnswerCompletionFactory
from app.services.qa.cached_answer_path import resolve_cached_answer
from app.services.qa.stream_answer_generation_factory import StreamAnswerGenerationFactory
from app.services.qa.stream_answer_run import StreamAnswerRun
from app.services.qa.stream_turn_factory import StreamTurnFactory
from app.services.qa.vision_evidence import resolve_vision_evidence
from app.services.qa.answer_styler import no_evidence_reply
from app.services.qa.stream_evidence_run import StreamEvidenceRun
from app.services.rag.base import BaseRAGService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.base import BaseTTSService

if TYPE_CHECKING:  # pragma: no cover
    from app.services.tts.streaming import StreamingTTSSession
    from app.services.tts.volcengine import (
        VolcengineStreamingTTSService,
        VolcengineStreamingTTSSession,
    )

logger = logging.getLogger(__name__)


@dataclass
class _PipelineRequestState:
    active_emotion: FusedEmotion
    active_response_policy: EmotionResponsePolicy
    active_text_emotion: EmotionSignal | None = None
    active_audio_emotion: EmotionSignal | None = None
    memory_prompt: str | None = None

class QAPipeline:
    def __init__(
        self,
        *,
        query_rewriter: QueryRewriter,
        faq_matcher: FAQMatcher,
        qa_cache: QACache,
        rag_service: BaseRAGService,
        llm_service: BaseLLMService,
        tts_service: BaseTTSService,
        avatar_service: BaseAvatarService,
        streaming_tts_service: StreamingTTSService | VolcengineStreamingTTSService | None = None,
        chat_log_repository: ChatLogRepository,
        visitor_repository: VisitorRepository | None = None,
        visitor_memory_repository: VisitorMemoryRepository | None = None,
        guided_selector: GuidedSelectionResolver,
        followup_suggestions: FollowUpSuggestionService,
        blind_spot_tracker: BlindSpotTracker | None = None,
        answer_cache_namespace: str = "default",
        llm_provider_name: str = "unknown",
        intent_router: IntentRouter | None = None,
        knowledge_repository: KnowledgeRepository | None = None,
        route_repository: RouteRepository | None = None,
        visibility_service=None,
        speech_profile: dict | None = None,
        vision_catalog=None,
        vision_site_id: str | None = None,
    ) -> None:
        self.query_rewriter = query_rewriter
        self.faq_matcher = faq_matcher
        self.qa_cache = qa_cache
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.avatar_service = avatar_service
        self.streaming_tts_service = streaming_tts_service
        self.chat_log_repository = chat_log_repository
        self.visitor_repository = visitor_repository
        self.visitor_memory_repository = visitor_memory_repository
        self.guided_selector = guided_selector
        self.followup_suggestions = followup_suggestions
        self.blind_spot_tracker = blind_spot_tracker
        self.answer_cache_namespace = answer_cache_namespace
        self.llm_provider_name = llm_provider_name or "unknown"
        self.intent_router = intent_router or IntentRouter()
        self.knowledge_repository = knowledge_repository
        self.route_repository = route_repository
        self.route_fast_path = StaticRouteAnswerBuilder(route_repository)
        self.visibility_service = visibility_service
        self.speech_profile = speech_profile
        self.vision_catalog = vision_catalog
        self.vision_site_id = vision_site_id
        self.text_emotion_analyzer = TextEmotionAnalyzer()
        self.emotion_fusion = MultimodalEmotionFusion()
        default_emotion = self.emotion_fusion.fuse(None, None)
        self._default_request_state = _PipelineRequestState(
            active_emotion=default_emotion,
            active_response_policy=response_policy_for(default_emotion),
        )
        self._request_state: ContextVar[_PipelineRequestState | None] = ContextVar(
            f"qa_pipeline_request_state_{id(self)}", default=None
        )
        self.final_answer_speech_emitter = FinalAnswerSpeechEmitter(
            tts_service=self.tts_service,
            avatar_service=self.avatar_service,
            audio_event_builder=self._build_audio_event,
            emotion_resolver=self._answer_emotion,
            epoch_is_current=self._epoch_is_current,
        )
        self.fast_path_answer_coordinator = FastPathAnswerCoordinator(
            speech_emitter=self.final_answer_speech_emitter,
            epoch_is_current=self._epoch_is_current,
        )
        self.stream_completion = StreamCompletionCoordinator()
        self.stream_turn_factory = StreamTurnFactory(
            llm_service=self.llm_service,
            streaming_tts_service=self.streaming_tts_service,
            audio_worker=self._queue_audio,
            adapt_tts_event=self._handle_streaming_tts_event,
            coerce_llm_event=self._coerce_llm_event,
        )

    def _current_request_state(self) -> _PipelineRequestState:
        return self._request_state.get() or self._default_request_state

    @property
    def _active_emotion(self) -> FusedEmotion:
        return self._current_request_state().active_emotion

    @_active_emotion.setter
    def _active_emotion(self, value: FusedEmotion) -> None:
        self._current_request_state().active_emotion = value

    @property
    def _active_response_policy(self) -> EmotionResponsePolicy:
        return self._current_request_state().active_response_policy

    @_active_response_policy.setter
    def _active_response_policy(self, value: EmotionResponsePolicy) -> None:
        self._current_request_state().active_response_policy = value

    @property
    def _active_text_emotion(self) -> EmotionSignal | None:
        return self._current_request_state().active_text_emotion

    @_active_text_emotion.setter
    def _active_text_emotion(self, value: EmotionSignal | None) -> None:
        self._current_request_state().active_text_emotion = value

    @property
    def _active_audio_emotion(self) -> EmotionSignal | None:
        return self._current_request_state().active_audio_emotion

    @_active_audio_emotion.setter
    def _active_audio_emotion(self, value: EmotionSignal | None) -> None:
        self._current_request_state().active_audio_emotion = value

    @property
    def _memory_prompt(self) -> str | None:
        return self._current_request_state().memory_prompt

    @_memory_prompt.setter
    def _memory_prompt(self, value: str | None) -> None:
        self._current_request_state().memory_prompt = value

    async def stream_chat(self, request: ChatRequest):
        token: Token[_PipelineRequestState | None] = self._request_state.set(
            _PipelineRequestState(
                active_emotion=self._default_request_state.active_emotion,
                active_response_policy=self._default_request_state.active_response_policy,
            )
        )
        try:
            async with aclosing(self._stream_chat(request)) as events:
                async for event in events:
                    yield event
        finally:
            self._request_state.reset(token)

    async def _stream_chat(self, request: ChatRequest):
        start = perf_counter()
        request_epoch = await self.visibility_service.read_epoch() if self.visibility_service is not None else None
        faq_epoch = getattr(self.faq_matcher, "knowledge_epoch", None)
        if request_epoch is not None and faq_epoch is not None and faq_epoch != request_epoch:
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return
        text_emotion = self.text_emotion_analyzer.analyze(request.query)
        audio_emotion = None
        if request.emotion_context is not None:
            audio_emotion = audio_emotion_signal(
                request.emotion_context.audio_emotion,
                request.emotion_context.audio_confidence,
                source=request.emotion_context.audio_source or "audio",
            )
        self._active_emotion = self.emotion_fusion.fuse(text_emotion, audio_emotion)
        self._active_response_policy = response_policy_for(self._active_emotion)
        self._active_text_emotion = text_emotion
        self._active_audio_emotion = audio_emotion
        resolved = await self.guided_selector.resolve(request.query, request.selection, request.context)
        if request.selection and request.selection.attraction_id is not None and "invalid_attraction_id" in resolved.warnings:
            yield StreamEvent(type="error", data={"code": "attraction_selection_stale", "message": "所选景点已不可用或更新，请重新选择。"})
            return
        audience = _resolve_narration_audience(request)

        # 跨会话记忆：仅当带了稳定 visitor_id 且仓储可用时读取。
        # 读失败不能影响回答，故整体 try/except 兜底。
        self._memory_prompt = None
        if self.visitor_memory_repository is not None and request.visitor_id:
            try:
                memory = await self.visitor_memory_repository.get(request.visitor_id)
                if memory is not None:
                    self._memory_prompt = (
                        build_memory_prompt(VisitorMemoryRepository.decode(memory)) or None
                    )
            except Exception:
                logger.exception("Visitor memory read failed; continuing without memory.")
                self._memory_prompt = None

        # 识别候选尚未经游客确认，也不能用模型自报置信度当成校准概率。
        # 避免将候选、旧选择或历史景点静默视为当前照片的事实。
        vision = request.vision_context
        vision_evidence = await resolve_vision_evidence(
            vision,
            resolved,
            vision_catalog=self.vision_catalog,
            vision_site_id=self.vision_site_id,
        )
        if vision_evidence.error_code is not None:
            yield StreamEvent(
                type="error",
                data={"code": vision_evidence.error_code, "message": vision_evidence.error_message},
            )
            return
        resolved = vision_evidence.resolved
        confirmed_visual_title = vision_evidence.confirmed_title

        yield StreamEvent(type="context", data=resolved.to_event_data())
        yield StreamEvent(
            type="emotion",
            data={
                **self._active_emotion.to_dict(),
                "response_strategy": self._active_response_policy.label.value,
                "avatar_emotion": self._active_response_policy.avatar_emotion,
            },
        )

        query_context = resolve_request_query_context(
            request,
            resolved,
            vision=vision,
            query_rewriter=self.query_rewriter,
            intent_router=self.intent_router,
        )
        retrieval_query = query_context.retrieval_query
        normalized_query = query_context.normalized_query
        intent_decision = query_context.intent_decision
        yield StreamEvent(
            type="intent",
            data={
                "intent": intent_decision.intent,
                "confidence": intent_decision.confidence,
                "matched_keywords": list(intent_decision.matched_keywords),
            },
        )

        # No verified live schedule is connected. Do not present static FAQ,
        # cached answers, or retrieved schedules as current opening hours.
        schedule_answer = resolve_unverified_schedule_answer(request.query)
        if schedule_answer is not None:
            answer_events = self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer=schedule_answer,
                sources=[], hit_level="schedule_unverified", start=start,
                resolved=resolved, expected_epoch=request_epoch,
            )
            async with aclosing(answer_events) as events:
                async for event in events:
                    yield event
            return

        ticket_answer = resolve_ticket_answer(request.query)
        if ticket_answer is not None:
            answer_events = self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer=ticket_answer,
                sources=[], hit_level="ticket_unverified", start=start,
                resolved=resolved, expected_epoch=request_epoch,
            )
            async with aclosing(answer_events) as events:
                async for event in events:
                    yield event
            return

        if vision is None and intent_decision.intent == "static_route":
            static_route = await self._build_static_route_answer(request)
            if static_route is not None:
                answer, route_sources = static_route
                yield StreamEvent(type="status", data={"text": "正在整理游览路线..."})
                answer_events = self._emit_final_answer(
                    request=request,
                    normalized_query=normalized_query,
                    answer=answer,
                    sources=route_sources,
                    hit_level="static_route" if route_sources else "route_clarification",
                    start=start,
                    resolved=resolved,
                    expected_epoch=request_epoch,
                )
                async with aclosing(answer_events) as events:
                    async for event in events:
                        yield event
                return
        cache_key = build_selection_cache_key(
            normalized_query,
            resolved.selection,
            answer_namespace=self.answer_cache_namespace,
            audience=audience,
            persona=request.persona,
            original_query=request.query,
        )
        yield StreamEvent(type="status", data={"text": "正在查找答案..."})

        scoped_attraction = resolved.scope is not None and resolved.scope.source_entry_id is not None
        faq_path = resolve_faq_path_for_request(
            self.faq_matcher,
            normalized_query,
            audience=audience,
            persona=request.persona,
            vision_present=vision is not None,
            scoped_attraction=scoped_attraction,
        )
        faq_documents = faq_path.documents if faq_path is not None else None
        faq_sources = faq_path.sources if faq_path is not None else []
        if faq_path is not None and faq_path.answer is not None:
            if not await self._epoch_is_current(request_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                return
            answer_events = self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=faq_path.answer,
                sources=faq_path.sources,
                hit_level=faq_path.hit_level,
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            )
            async with aclosing(answer_events) as events:
                async for event in events:
                    yield event
            return

        # Visitor memory influences generated wording and must never cross the
        # shared cache boundary or be bypassed by a generic cached answer.
        cache_allowed = shared_cache_allowed(
            vision_present=vision is not None,
            memory_prompt=self._memory_prompt,
            neutral=self._active_emotion.label == EmotionLabel.NEUTRAL,
        )
        cached = await resolve_cached_answer(
            cache=self.qa_cache,
            cache_key=cache_key,
            allowed=cache_allowed,
            epoch=request_epoch,
            epoch_is_current=lambda: self._epoch_is_current(request_epoch),
            persona=request.persona,
        )
        if cached is not None and cached.stale:
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return
        if cached is not None:
            if cached.answer is None:
                raise RuntimeError("current cached answer is missing its resolved text")
            answer_events = self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=cached.answer,
                sources=cached.sources,
                hit_level="cache",
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            )
            async with aclosing(answer_events) as events:
                async for event in events:
                    yield event
            return

        evidence_run = StreamEvidenceRun(
            rag_service=self.rag_service,
            query=retrieval_query,
            normalized_query=normalized_query,
            scope=resolved.scope,
            faq_documents=faq_documents,
            faq_sources=faq_sources,
            epoch_is_current=lambda: self._epoch_is_current(request_epoch),
        )
        async with aclosing(evidence_run.events()) as evidence_events:
            async for event in evidence_events:
                yield event
        evidence_outcome = evidence_run.outcome
        if evidence_outcome is None:
            raise RuntimeError("evidence selection ended without an outcome")
        if evidence_outcome.error_event is not None:
            return
        documents = evidence_outcome.documents
        sources = evidence_outcome.sources

        if not documents:
            if self.blind_spot_tracker is not None:
                try:
                    await self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="rag_no_docs",
                )
                    logger.info("Blind spot recorded (RAG no docs)")
                except Exception:
                    logger.exception("Knowledge blind spot recording failed")
            answer = no_evidence_reply(request.persona)
            answer_events = self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=answer,
                sources=[],
                hit_level="rag_insufficient",
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            )
            async with aclosing(answer_events) as events:
                async for event in events:
                    yield event
            return

        # FAQ 走 LLM 改写时保留可观测的命中来源，便于与纯 FAQ 快路径区分。
        llm_hit_level = faq_path.hit_level if faq_documents is not None and faq_path is not None else "rag"
        generation_run = StreamAnswerGenerationFactory(
            turn_factory=self.stream_turn_factory,
            llm_provider_name=self.llm_provider_name,
            emotion_aware_query=self._emotion_aware_query,
            epoch_is_current=lambda: self._epoch_is_current(request_epoch),
        ).build(
            request=request,
            documents=documents,
            audience=audience,
            memory=self._memory_prompt,
            confirmed_visual_title=confirmed_visual_title,
            vision_context_present=vision is not None,
            faq_documents_present=faq_documents is not None,
            cache_allowed=cache_allowed,
            llm_hit_level=llm_hit_level,
            fallback_hit_level=f"{llm_hit_level}_llm_fallback",
            faq_answer=faq_path.source_answer if faq_path is not None else "",
            faq_sources=faq_sources,
        )
        completion_factory = StreamAnswerCompletionFactory(
            completion=self.stream_completion,
            cache_writer=lambda answer, bound_sources, epoch: self.qa_cache.set(
                cache_key, answer, bound_sources, epoch=epoch
            ),
            persist_interaction=self._persist_interaction,
            blind_spot_tracker=self.blind_spot_tracker,
            request=request,
            normalized_query=normalized_query,
            sources=sources,
            expected_epoch=request_epoch,
            start=start,
            active_subject=resolved.active_subject,
            followup_event=lambda: self._followup_event(resolved),
            done_event_builder=self._done_event,
            faq_documents_present=faq_documents is not None,
            text_only=request.text_only,
            epoch_is_current=lambda: self._epoch_is_current(request_epoch),
        )
        answer_run = StreamAnswerRun(
            generation_run=generation_run,
            completion_factory=completion_factory.build,
        )
        async with aclosing(answer_run.events()) as answer_events:
            async for event in answer_events:
                yield event

    async def _build_static_route_answer(self, request: ChatRequest) -> tuple[str, list[dict]] | None:
        """保留旧调用入口，将静态路线回答委托给独立业务节点。"""
        return await self.route_fast_path.build_answer(request)

    async def _emit_final_answer(
        self,
        *,
        request: ChatRequest,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        start: float,
        resolved: ResolvedInteraction,
        expected_epoch: int | None = None,
    ):
        def prepare_answer(value: str, bound_sources: list[dict]) -> str:
            return self._ensure_inline_citations(
                apply_answer_prefix(value, self._active_response_policy), bound_sources
            )

        async def persist_answer(value: str, latency_ms: int) -> int:
            return await self._persist_interaction(
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
            return self._done_event(
                chat_log_id=chat_log_id,
                hit_level=hit_level,
                total_ms=latency_ms,
                degraded=hit_level in {"rag_insufficient", "rag_llm_fallback", "schedule_unverified", "ticket_unverified"},
                provider="local" if hit_level.startswith("faq_") or hit_level in {"cache", "schedule_unverified", "ticket_unverified", "static_route", "route_clarification"} else "rag",
            )

        answer_events = self.fast_path_answer_coordinator.events(
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            text_only=request.text_only,
            expected_epoch=expected_epoch,
            start=start,
            prepare_answer=prepare_answer,
            persist_answer=persist_answer,
            followups_event=lambda: self._followup_event(resolved),
            done_event=done_event,
        )
        async with aclosing(answer_events) as events:
            async for event in events:
                yield event

    async def _epoch_is_current(self, expected_epoch: int | None) -> bool:
        if expected_epoch is None or self.visibility_service is None:
            return True
        return await self.visibility_service.read_epoch() == expected_epoch

    async def _persist_interaction(
        self,
        *,
        session_id: str,
        raw_query: str,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        latency_ms: int,
        request: ChatRequest,
        active_subject: str | None = None,
    ) -> int:
        """Persist every completed branch before exposing its completion event."""
        create_kwargs = dict(
            session_id=session_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            latency_ms=latency_ms,
        )
        if self.speech_profile is not None and not request.text_only:
            from app.services.tts.speech_profile import answer_fingerprint, build_speech_cache_key

            metadata = dict(self.speech_profile)
            metadata["answer_version"] = answer_fingerprint(answer)
            metadata["cache_key"] = build_speech_cache_key(answer, self.speech_profile)
            create_kwargs["speech_metadata"] = metadata
        if isinstance(self.chat_log_repository, ChatLogRepository):
            create_kwargs.update(
                input_mode=request.input_mode,
                text_emotion=(
                    self._active_text_emotion.label.value
                    if self._active_text_emotion is not None
                    else "neutral"
                ),
                audio_emotion=(
                    self._active_audio_emotion.label.value
                    if self._active_audio_emotion is not None and self._active_audio_emotion.available
                    else None
                ),
                fused_emotion=self._active_emotion.label.value,
                emotion_confidence=self._active_emotion.confidence,
                emotion_intensity=self._active_emotion.intensity,
                emotion_conflict=self._active_emotion.conflict,
                emotion_modalities=list(self._active_emotion.modalities),
                response_strategy=self._active_response_policy.label.value,
            )
        log = await self.chat_log_repository.create(**create_kwargs)
        if self.visitor_repository is not None:
            try:
                await self.visitor_repository.upsert(
                    session_id=session_id,
                    interests=_extract_interests(request),
                    audience_type=_infer_audience_type(request),
                )
            except Exception:
                logger.exception("Visitor profile update failed.")
        if self.visitor_memory_repository is not None and request.visitor_id:
            try:
                await self.visitor_memory_repository.record_visit(
                    visitor_id=request.visitor_id,
                    session_id=session_id,
                    attraction_title=active_subject,
                    interests=_extract_interests(request),
                    narration_audience=_resolve_narration_audience(request),
                )
            except Exception:
                logger.exception("Visitor memory write failed.")
        return log.id

    @staticmethod
    def _done_event(
        *,
        chat_log_id: int,
        hit_level: str,
        total_ms: int,
        degraded: bool = False,
        provider: str = "local",
        completion: str = "complete",
    ) -> StreamEvent:
        return StreamEvent(
            type="done",
            data={
                "chat_log_id": chat_log_id,
                "hit_level": hit_level,
                "total_ms": total_ms,
                "degraded": degraded,
                "provider": provider,
                "completion": completion,
            },
        )

    async def _queue_audio(
        self, sentence: str, queue: QueuedStreamEvents, *,
        previous: asyncio.Task[None] | None = None, semaphore: asyncio.Semaphore | None = None,
        notify=None,
    ) -> None:
        async def synthesize():
            try:
                return await self.tts_service.synthesize(sentence)
            except Exception:
                logger.exception("TTS sentence synthesis failed; preserving text")
                from app.services.tts.base import TTSAudio
                return TTSAudio(base64_audio="", duration_ms=0, provider="tts_unavailable")

        if semaphore is None:
            audio = await synthesize()
        else:
            async with semaphore:
                audio = await synthesize()
        avatar = await self.avatar_service.drive(sentence)
        if previous is not None:
            await previous
        await queue.publish(
            (
                StreamEvent(type="avatar", data={
                    "viseme_text": avatar.viseme_text,
                    "emotion": self._active_response_policy.avatar_emotion,
                }),
                self._build_audio_event(
                    sentence,
                    audio.base64_audio,
                    audio.duration_ms,
                    audio.provider,
                ),
            ),
            notify=notify,
        )

    @staticmethod
    def _build_audio_event(
        text: str,
        base64_audio: str,
        duration_ms: int,
        provider: str = "unknown",
    ) -> StreamEvent:
        return build_speech_audio_event(
            text,
            base64_audio,
            duration_ms,
            provider,
            viseme_timeline_builder=build_speech_viseme_timeline,
        )

    @staticmethod
    def _build_viseme_timeline(text: str, duration_ms: int) -> list[dict]:
        return build_speech_viseme_timeline(text, duration_ms)

    @staticmethod
    def _words_to_viseme_timeline(words: list[dict]) -> list[dict]:
        return build_words_viseme_timeline(words)

    def _handle_streaming_tts_event(self, tts_event) -> list[StreamEvent]:
        return adapt_streaming_tts_event(
            tts_event,
            avatar_emotion=self._active_response_policy.avatar_emotion,
            word_viseme_timeline_builder=build_words_viseme_timeline,
        )

    def _answer_emotion(self, hit_level: str | None, source_count: int) -> str:
        """根据回答路径决定数字人情感"""
        if self._active_emotion.label != EmotionLabel.NEUTRAL:
            return self._active_response_policy.avatar_emotion
        if hit_level is None and source_count == 0:
            return "apology"
        if hit_level and hit_level.startswith("faq_"):
            return "happy"
        if hit_level == "rag_evidence" and source_count >= 2:
            return "happy"
        if hit_level == "rag_evidence":
            return "speaking"
        if hit_level == "stub" or hit_level == "fallback":
            return "apology"
        return "speaking"

    def _emotion_aware_query(self, query: str) -> str:
        if self._active_emotion.label == EmotionLabel.NEUTRAL:
            return query
        return (
            f"{query}\n\n"
            f"[服务表达要求：{self._active_response_policy.prompt_guidance} "
            "只调整表达和信息优先级，不要声称看见或诊断了游客情绪。]"
        )

    @staticmethod
    def _coerce_llm_event(item: LLMStreamEvent | str) -> LLMStreamEvent:
        if isinstance(item, LLMStreamEvent):
            return item
        return LLMStreamEvent(type="content", text=str(item))

    @staticmethod
    def _ensure_inline_citations(answer: str, sources: list[dict]) -> str:
        # Retrieval sources remain available in the sources event and chat log.
        # Adding citation markers here would assert support that was not checked.
        return answer

    def _followup_event(self, resolved: ResolvedInteraction) -> StreamEvent:
        return StreamEvent(
            type="followups",
            data={"items": self.followup_suggestions.generate(resolved)},
        )
