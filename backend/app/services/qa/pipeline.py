from __future__ import annotations

import asyncio
import json
import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from app.repositories.chat_log import ChatLogRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.repositories.visitor_memory import VisitorMemoryRepository
from app.schemas.chat import ChatRequest, ConversationContext
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
    resolve_faq_path,
    resolve_ticket_answer,
    resolve_unverified_schedule_answer,
    shared_cache_allowed,
)
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
from app.services.qa.route_fast_path import StaticRouteAnswerBuilder
from app.services.qa.speech_event_adapter import (
    build_audio_event as build_speech_audio_event,
    build_viseme_timeline as build_speech_viseme_timeline,
    handle_streaming_tts_event as adapt_streaming_tts_event,
    words_to_viseme_timeline as build_words_viseme_timeline,
)
from app.services.qa.stream_events import StreamEvent
from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_completion import final_audio_segments
from app.services.qa.stream_lifecycle import AudioTaskGroup, StreamProducerGroup
from app.services.qa.stream_mux import StreamMuxState
from app.services.qa.stream_mux_consumer import StreamMuxConsumer
from app.services.qa.streaming_tts_buffer import StreamingTTSBuffer
from app.services.qa.streaming_tts_controller import StreamingTTSController
from app.services.qa.vision_evidence import resolve_vision_evidence
from app.services.qa.answer_styler import polish_answer, no_evidence_reply
from app.services.qa.evidence_retrieval import retrieve_evidence
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
            async for event in self._stream_chat(request):
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

        rewrite_context = None if vision is not None else request.context
        if resolved.active_subject:
            rewrite_context = ConversationContext(
                last_subject=resolved.active_subject,
                history_summary=request.context.history_summary if request.context else None,
            )
        retrieval_query = request.query
        if vision is not None:
            hint = vision.retrieval_query.strip()[:1000]
            if hint and hint not in retrieval_query:
                retrieval_query = f"{retrieval_query}\n{hint}"
        normalized_query = self.query_rewriter.rewrite(retrieval_query, rewrite_context)
        intent_decision = self.intent_router.detect(request.query, resolved.selection)
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
            async for event in self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer=schedule_answer,
                sources=[], hit_level="schedule_unverified", start=start,
                resolved=resolved, expected_epoch=request_epoch,
            ):
                yield event
            return

        ticket_answer = resolve_ticket_answer(request.query)
        if ticket_answer is not None:
            async for event in self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer=ticket_answer,
                sources=[], hit_level="ticket_unverified", start=start,
                resolved=resolved, expected_epoch=request_epoch,
            ):
                yield event
            return

        if vision is None and intent_decision.intent == "static_route":
            static_route = await self._build_static_route_answer(request)
            if static_route is not None:
                answer, route_sources = static_route
                yield StreamEvent(type="status", data={"text": "正在整理游览路线..."})
                async for event in self._emit_final_answer(
                    request=request,
                    normalized_query=normalized_query,
                    answer=answer,
                    sources=route_sources,
                    hit_level="static_route" if route_sources else "route_clarification",
                    start=start,
                    resolved=resolved,
                    expected_epoch=request_epoch,
                ):
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

        # FAQ records do not carry a verifiable attraction binding. A scoped
        # question must use scoped retrieval rather than a potentially general FAQ.
        scoped_attraction = resolved.scope is not None and resolved.scope.source_entry_id is not None
        faq_result = self.faq_matcher.match(normalized_query) if vision is None and not scoped_attraction else None
        faq_path = resolve_faq_path(
            faq_result,
            audience=audience,
            persona=request.persona,
        )
        faq_documents = faq_path.documents if faq_path is not None else None
        faq_sources = faq_path.sources if faq_path is not None else []
        if faq_path is not None and faq_path.answer is not None:
            if not await self._epoch_is_current(request_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                return
            async for event in self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=faq_path.answer,
                sources=faq_path.sources,
                hit_level=faq_path.hit_level,
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            ):
                yield event
            return

        # Visitor memory influences generated wording and must never cross the
        # shared cache boundary or be bypassed by a generic cached answer.
        cache_allowed = shared_cache_allowed(
            vision_present=vision is not None,
            memory_prompt=self._memory_prompt,
            neutral=self._active_emotion.label == EmotionLabel.NEUTRAL,
        )
        cached = await self.qa_cache.get(cache_key, epoch=request_epoch) if cache_allowed else None
        if cached:
            if not await self._epoch_is_current(request_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                return
            styled_answer = polish_answer(cached.answer, request.persona, cached.sources)
            async for event in self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=styled_answer,
                sources=cached.sources,
                hit_level="cache",
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            ):
                yield event
            return

        if faq_documents is not None:
            yield StreamEvent(type="status", data={"text": "正在按你的讲解方式改写..."})
            documents = faq_documents
            sources = faq_sources
            if not await self._epoch_is_current(request_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                return
            if faq_sources:
                yield StreamEvent(type="sources", data={"docs": faq_sources})
        else:
            yield StreamEvent(type="status", data={"text": "正在检索景区知识..."})
            evidence = await retrieve_evidence(
                self.rag_service,
                query=retrieval_query,
                normalized_query=normalized_query,
                scope=resolved.scope,
            )
            documents = evidence.documents
            sources = evidence.sources
            if not await self._epoch_is_current(request_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                return
            if sources:
                yield StreamEvent(type="sources", data={"docs": sources})

        if not await self._epoch_is_current(request_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return

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
            async for event in self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=answer,
                sources=[],
                hit_level="rag_insufficient",
                start=start,
                resolved=resolved,
                expected_epoch=request_epoch,
            ):
                yield event
            return

        # FAQ 走 LLM 改写时保留可观测的命中来源，便于与纯 FAQ 快路径区分。
        llm_hit_level = faq_path.hit_level if faq_documents is not None and faq_path is not None else "rag"
        llm_fallback_hit_level = f"{llm_hit_level}_llm_fallback"

        answer_stream = StreamAnswerBuffer()
        audio_events = QueuedStreamEvents()
        audio_group = AudioTaskGroup(
            lambda sentence, **kwargs: self._queue_audio(sentence, audio_events, **kwargs)
        )

        def schedule_audio(sentence: str) -> None:
            audio_group.schedule(sentence, notify=notify_audio)

        async def notify_audio() -> None:
            await mux_queue.put(("audio_ready", None))

        async def cancel_audio() -> None:
            await audio_group.cancel()

        # ── 流式 TTS 路径 ──
        tts_stream: StreamingTTSSession | VolcengineStreamingTTSSession | None = None
        streaming_requested = (
            self.streaming_tts_service is not None
            and not request.text_only
            and faq_documents is None
        )
        if streaming_requested and self.streaming_tts_service is not None:
            tts_stream = self.streaming_tts_service.create_session()

        mux_queue: asyncio.Queue[tuple[str, object | None]] = asyncio.Queue()
        tts_finish_requested = asyncio.Event()

        generation_query = request.query
        if confirmed_visual_title is not None:
            # Catalog title is data, not an instruction; JSON escaping
            # prevents its content from changing this context's shape.
            title_data = json.dumps(confirmed_visual_title, ensure_ascii=False)
            generation_query = (
                "游客已从已发布目录确认本次讲解的景点名称（JSON字符串）："
                f"{title_data}。图片识别线索未经确认，仅用于检索，不得作为事实；"
                "回答只能根据参考资料，资料不足时明确说明。\n"
                f"游客原始问题：{request.query}"
            )
        elif vision is not None:
            generation_query = (
                "图片识别线索未经确认，仅用于检索；不要断言照片中的景点身份。"
                "只能依据参考资料提供有条件的说明，身份不明确时请游客选择或确认景点。\n"
                f"游客原始问题：{request.query}"
            )
        llm_source = self.llm_service.stream_generate(
            self._emotion_aware_query(generation_query),
            documents,
            persona=request.persona,
            audience=audience,
            memory=self._memory_prompt,
        )

        stream_producers = StreamProducerGroup(mux_queue)
        stream_producers.start_llm(llm_source)
        if tts_stream is not None:
            stream_producers.start_tts(tts_stream, tts_finish_requested)
        mux_state = StreamMuxState(streaming_requested=streaming_requested)
        streaming_tts_buffer = StreamingTTSBuffer()
        streaming_tts_controller = StreamingTTSController(
            tts_stream, mux_state, streaming_tts_buffer, tts_finish_requested
        )
        stream_consumer = StreamMuxConsumer(
            queue=mux_queue,
            mux_state=mux_state,
            epoch_is_current=lambda: self._epoch_is_current(request_epoch),
            answer_buffer=answer_stream,
            audio_events=audio_events,
            schedule_audio=schedule_audio,
            streaming_tts_buffer=streaming_tts_buffer,
            streaming_tts_controller=streaming_tts_controller,
            streaming_requested=streaming_requested,
            text_only=request.text_only,
            faq_documents_present=faq_documents is not None,
            adapt_tts_event=self._handle_streaming_tts_event,
            coerce_llm_event=self._coerce_llm_event,
        )

        try:
            async for event in stream_consumer.events():
                yield event
        except BaseException:
            await cancel_audio()
            raise
        finally:
            await stream_producers.close()

        llm_usage = stream_consumer.llm_usage
        llm_finish_reason = stream_consumer.llm_finish_reason
        if mux_state.llm_error is not None:
            await cancel_audio()
            raise mux_state.llm_error
        if stream_consumer.visibility_changed:
            await cancel_audio()
            yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
            return

        degraded_llm = bool(
            llm_finish_reason
            and (
                llm_finish_reason.startswith("fallback_")
                or llm_finish_reason.startswith("interrupted_")
            )
        )
        if degraded_llm and faq_documents is not None:
            # Do not speak a partial rewrite that will be replaced by the FAQ.
            answer_stream.full_answer = polish_answer(faq_result.answer, request.persona, faq_sources)

        faq_text_sent = faq_documents is not None
        if faq_text_sent:
            yield StreamEvent(type="text", data={"text": answer_stream.full_answer, "is_complete": True})

        for text in final_audio_segments(
            answer_stream,
            faq_documents_present=faq_documents is not None,
            text_only=request.text_only,
            streaming_requested=streaming_requested,
            streaming_tts_failed=mux_state.tts_failed,
            tts_confirmed_chars=mux_state.tts_confirmed_chars,
        ):
            schedule_audio(text)

        try:
            for task in audio_group.tasks:
                await task
                if not await self._epoch_is_current(request_epoch):
                    await cancel_audio()
                    yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
                    return
                for audio_event in audio_events.drain():
                    yield audio_event
        except BaseException:
            await cancel_audio()
            raise

        if degraded_llm and self.blind_spot_tracker is not None:
            try:
                await self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="llm_fallback",
                )
                logger.info("Blind spot recorded (LLM degraded)")
            except Exception:
                logger.exception("Knowledge blind spot recording failed")
        if degraded_llm and faq_documents is not None:
            # FAQ 按受众改写失败时，不能把"AI讲解服务暂时不可用"甩给游客：
            # FAQ 原文本身权威且完整，直接回落原文——风格没换成，但内容正确。
            # 刻意保持 degraded_llm=True，避免把未改写的答案写进受众专属缓存，
            # 否则一次 LLM 抖动就会长期污染该受众的缓存。
            answer_stream.full_answer = polish_answer(faq_result.answer, request.persona, faq_sources)
        if not await self._epoch_is_current(request_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
            return
        if cache_allowed and not degraded_llm:
            await self.qa_cache.set(cache_key, answer_stream.full_answer, sources, epoch=request_epoch)
        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await self._persist_interaction(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=answer_stream.full_answer,
            sources=sources,
            hit_level=llm_fallback_hit_level if degraded_llm else llm_hit_level,
            latency_ms=latency_ms,
            request=request,
            active_subject=resolved.active_subject,
        )
        if not await self._epoch_is_current(request_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
            return
        logger.info(
            "LLM completed: finish_reason=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s cached_tokens=%s",
            llm_finish_reason,
            llm_usage.prompt_tokens,
            llm_usage.completion_tokens,
            llm_usage.total_tokens,
            llm_usage.cached_tokens,
        )
        incomplete = bool(
            llm_finish_reason and llm_finish_reason.startswith("interrupted_") and faq_documents is None
        )
        if not faq_text_sent:
            yield StreamEvent(type="text", data={"text": answer_stream.full_answer, "is_complete": not incomplete})
        yield self._followup_event(resolved)
        yield self._done_event(
            chat_log_id=chat_log_id,
            hit_level=llm_fallback_hit_level if degraded_llm else llm_hit_level,
            total_ms=latency_ms,
            degraded=degraded_llm,
            provider=self.llm_provider_name if not degraded_llm else "evidence_fallback",
            completion="incomplete" if incomplete else "complete",
        )

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
        if not await self._epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return
        answer = apply_answer_prefix(answer, self._active_response_policy)
        answer = self._ensure_inline_citations(answer, sources)
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})
        if not await self._epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return
        yield StreamEvent(type="text", data={"text": answer, "is_complete": True})
        if not request.text_only:
            # 景点讲解（FAQ路径）用简短摘要做 TTS，避免长文本合成慢
            tts_text = answer
            if hit_level.startswith("faq_") and len(answer) > 150:
                # 截断到前 150 字，在句号处断开
                tts_text = answer[:150]
                last_period = tts_text.rfind("。")
                if last_period > 80:
                    tts_text = tts_text[: last_period + 1]
                else:
                    tts_text = tts_text.rstrip() + "……"

            # TTS 和数字人驱动并行执行
            audio_task = self.tts_service.synthesize(tts_text)
            avatar_task = self.avatar_service.drive(tts_text)
            audio, avatar = await asyncio.gather(audio_task, avatar_task)

            if not await self._epoch_is_current(expected_epoch):
                yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
                return

            emotion = self._answer_emotion(hit_level, len(sources))
            avatar_data = {"viseme_text": avatar.viseme_text, "emotion": emotion}
            if avatar.action:
                avatar_data["action"] = avatar.action
            yield StreamEvent(type="avatar", data=avatar_data)
            yield self._build_audio_event(
                tts_text,
                audio.base64_audio,
                audio.duration_ms,
                audio.provider,
            )

        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await self._persist_interaction(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            latency_ms=latency_ms,
            request=request,
            active_subject=resolved.active_subject,
        )
        yield self._followup_event(resolved)
        yield self._done_event(
            chat_log_id=chat_log_id,
            hit_level=hit_level,
            total_ms=latency_ms,
            degraded=hit_level in {"rag_insufficient", "rag_llm_fallback", "schedule_unverified", "ticket_unverified"},
            provider="local" if hit_level.startswith("faq_") or hit_level in {"cache", "schedule_unverified", "ticket_unverified", "static_route", "route_clarification"} else "rag",
        )

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
