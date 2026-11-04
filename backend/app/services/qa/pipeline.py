from __future__ import annotations

import asyncio
import base64
import json
import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from asyncio import QueueEmpty
from time import perf_counter
from typing import TYPE_CHECKING

# ── 拼音导入缓存 ──
_PINYIN_FN = None
_PINYIN_CHECKED = False
_FINALS_STYLE = None


def _get_pinyin():
    global _PINYIN_FN, _PINYIN_CHECKED
    if not _PINYIN_CHECKED:
        _PINYIN_CHECKED = True
        try:
            from pypinyin import pinyin as _p
            _PINYIN_FN = _p
        except ImportError:
            pass
    return _PINYIN_FN


def _get_finals_style():
    global _FINALS_STYLE
    if _FINALS_STYLE is None:
        try:
            from pypinyin import Style
            _FINALS_STYLE = Style.FINALS
        except ImportError:
            _FINALS_STYLE = -1
    return _FINALS_STYLE

from app.repositories.chat_log import ChatLogRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.repositories.visitor_memory import VisitorMemoryRepository
from app.schemas.chat import ChatRequest, ConversationContext
from app.services.avatar.base import BaseAvatarService
from app.services.avatar.viseme import build_viseme_timeline, build_viseme_timeline_fallback
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_builder import get_audience_style
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
from app.services.qa.faq_matcher import FAQMatchResult, FAQMatcher
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
from app.services.qa.stream_events import StreamEvent
from app.services.qa.answer_styler import polish_answer, no_evidence_reply
from app.services.rag.base import BaseRAGService, RetrievedDocument, RetrievalScope
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

def _faq_evidence_document(match: FAQMatchResult) -> RetrievedDocument:
    """把 FAQ 答复包装成一条检索资料。

    用途：受众非默认时，让 LLM 基于这条唯一证据换说法（分众化），
    事实仍完全来自 FAQ 原文，不引入任何新资料。
    """
    return RetrievedDocument(
        title="常见问题资料",
        content=match.answer,
        snippet=match.answer,
        source="、".join(match.sources) or "常见问题资料（未标注来源）",
        score=1.0,
    )


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
        confirmed_visual_title = None
        if vision is not None and vision.confirmation is not None:
            confirmation = vision.confirmation
            selected_spot = None
            if self.vision_catalog is not None and confirmation.site_id == self.vision_site_id:
                try:
                    catalog = await self.vision_catalog.list_for_site(self.vision_site_id)
                    selected_spot = next((item for item in catalog.entries if item.site_id == self.vision_site_id and item.spot_code == confirmation.spot_code and item.published_revision_id == confirmation.published_revision_id), None)
                except Exception:
                    logger.exception("Confirmed visual attraction catalog lookup failed")
            if selected_spot is None or not selected_spot.entry_id.isdigit() or int(selected_spot.entry_id) < 1:
                yield StreamEvent(type="error", data={"code": "vision_confirmation_stale", "message": "景点已下架、更新或不属于当前景区，请重新选择。"})
                return
            confirmed_visual_title = selected_spot.title
            resolved = ResolvedInteraction(
                selection=resolved.selection,
                scope=RetrievalScope(source_entry_id=int(selected_spot.entry_id)),
                resolution_source="selection",
                active_subject=selected_spot.title,
                warnings=resolved.warnings,
            )
        elif vision is not None:
            resolved = ResolvedInteraction(
                selection=resolved.selection,
                scope=None,
                resolution_source=resolved.resolution_source,
                active_subject=None,
                warnings=(*resolved.warnings, "vision_scope_unconfirmed"),
            )

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
        schedule_terms = ("开放时间", "营业时间", "演出时间", "什么时候开放", "几点开放", "几点开门", "几点关门")
        if any(term in request.query for term in schedule_terms):
            async for event in self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer="目前无法核实最新开放或演出时间，请以景区当日官方公告或现场咨询为准。",
                sources=[], hit_level="schedule_unverified", start=start,
                resolved=resolved, expected_epoch=request_epoch,
            ):
                yield event
            return

        ticket_terms = ("门票价格", "门票多少钱", "票价", "半价票", "免费入园")
        ticket_discount = "优惠政策" in request.query and any(term in request.query for term in ("门票", "购票", "票务"))
        if ticket_discount or any(term in request.query for term in ticket_terms):
            async for event in self._emit_final_answer(
                request=request, normalized_query=normalized_query,
                answer="目前无法核实最新票价和优惠条件，请以相关官方票务信息或现场咨询为准。",
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
        faq_documents: list[RetrievedDocument] | None = None
        faq_sources: list[dict] = []
        if faq_result is not None and faq_result.is_hit:
            faq_sources = [
                {
                    "evidence_id": f"证据{index}",
                    "title": "FAQ",
                    "snippet": faq_result.answer[:80],
                    "source": source,
                }
                for index, source in enumerate(faq_result.sources, start=1)
            ]
            if get_audience_style(audience):
                # 受众非默认（child/expert）：不能直接吐 FAQ 原文，否则"切讲解方式没反应"。
                # 改为把 FAQ 原文当作唯一证据交给 LLM 换风格——只换说法、不动事实。
                # adult/未指定仍走零延迟的原文快路径（get_audience_style 返回空串）。
                faq_documents = [_faq_evidence_document(faq_result)]
            else:
                styled_answer = polish_answer(faq_result.answer, request.persona, faq_sources)
                if not await self._epoch_is_current(request_epoch):
                    yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
                    return
                async for event in self._emit_final_answer(
                    request=request,
                    normalized_query=normalized_query,
                    answer=styled_answer,
                    sources=faq_sources,
                    hit_level=f"faq_{faq_result.level}",
                    start=start,
                    resolved=resolved,
                    expected_epoch=request_epoch,
                ):
                    yield event
                return

        # Visitor memory influences generated wording and must never cross the
        # shared cache boundary or be bypassed by a generic cached answer.
        shared_cache_allowed = (
            vision is None and self._memory_prompt is None
            and self._active_emotion.label == EmotionLabel.NEUTRAL
        )
        cached = await self.qa_cache.get(cache_key, epoch=request_epoch) if shared_cache_allowed else None
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
            documents = await self.rag_service.retrieve(
                retrieval_query,
                normalized_query=normalized_query,
                scope=resolved.scope,
            )
            sources = [
                self._doc_to_source(document, evidence_id=f"证据{index}")
                for index, document in enumerate(documents, start=1)
            ]
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
        llm_hit_level = f"faq_{faq_result.level}_styled" if faq_documents is not None else "rag"
        llm_fallback_hit_level = f"{llm_hit_level}_llm_fallback"

        full_answer = ""
        sentence_buffer = ""
        llm_usage = LLMUsage()
        llm_finish_reason: str | None = None
        audio_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        audio_tasks: list[asyncio.Task[None]] = []
        audio_concurrency = asyncio.Semaphore(3)

        def schedule_audio(sentence: str) -> None:
            previous = audio_tasks[-1] if audio_tasks else None
            audio_tasks.append(asyncio.create_task(
                self._queue_audio(sentence, audio_queue, previous=previous, semaphore=audio_concurrency, notify=notify_audio)
            ))

        async def notify_audio() -> None:
            await mux_queue.put(("audio_ready", None))

        async def cancel_audio() -> None:
            for task in audio_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*audio_tasks, return_exceptions=True)

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

        async def produce_llm_events() -> None:
            try:
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
                async for item in self.llm_service.stream_generate(
                    self._emotion_aware_query(generation_query),
                    documents,
                    persona=request.persona,
                    audience=audience,
                    memory=self._memory_prompt,
                ):
                    await mux_queue.put(("llm", item))
            except Exception as exc:
                await mux_queue.put(("llm_error", exc))
            finally:
                await mux_queue.put(("llm_done", None))

        async def connect_and_forward_tts_events() -> None:
            assert tts_stream is not None
            try:
                await tts_stream.connect()
                await mux_queue.put(("tts_connected", None))
                finish_wait_started: float | None = None
                while True:
                    event = await tts_stream.receive(timeout=1.0)
                    if event is None:
                        if tts_finish_requested.is_set():
                            finish_wait_started = finish_wait_started or asyncio.get_running_loop().time()
                            if asyncio.get_running_loop().time() - finish_wait_started >= 12.0:
                                raise TimeoutError("流式 TTS 完成事件等待超时")
                        continue
                    await mux_queue.put(("tts", event))
                    if event.type in {"done", "error"}:
                        break
            except Exception as exc:
                await mux_queue.put(("tts_connect_error", exc))

        llm_task = asyncio.create_task(produce_llm_events())
        tts_task = (
            asyncio.create_task(connect_and_forward_tts_events())
            if tts_stream is not None
            else None
        )
        llm_done = False
        visibility_changed = False
        llm_error: Exception | None = None
        tts_connected = False
        tts_done = not streaming_requested
        tts_failed = False
        tts_finish_sent = False
        tts_text_buffer = ""
        tts_confirmed_chars = 0

        try:
            while not llm_done or not tts_done:
                if not await self._epoch_is_current(request_epoch):
                    visibility_changed = True
                    break
                kind, payload = await mux_queue.get()
                if not await self._epoch_is_current(request_epoch):
                    visibility_changed = True
                    break

                if kind == "llm":
                    event = self._coerce_llm_event(payload)
                elif kind == "llm_error":
                    llm_error = payload if isinstance(payload, Exception) else RuntimeError("LLM stream failed")
                    continue
                elif kind == "llm_done":
                    llm_done = True
                    event = None
                elif kind == "tts_connected":
                    tts_connected = True
                    logger.info("Streaming TTS session started for chat")
                    event = None
                elif kind == "tts_connect_error":
                    tts_failed = True
                    tts_done = True
                    logger.warning("Streaming TTS unavailable; HTTP fallback will synthesize remaining text: %s", type(payload).__name__)
                    event = None
                elif kind == "tts":
                    tts_event = payload
                    if getattr(tts_event, "type", "") == "word_timestamps":
                        timestamp_data = getattr(tts_event, "data", {}) or {}
                        if isinstance(timestamp_data, dict):
                            tts_confirmed_chars = max(
                                tts_confirmed_chars,
                                int(timestamp_data.get("characters", 0) or 0),
                            )
                    if getattr(tts_event, "type", "") == "error":
                        tts_failed = True
                        tts_done = True
                        logger.warning("Streaming TTS failed mid-response; HTTP fallback will synthesize remaining text")
                    elif getattr(tts_event, "type", "") == "done":
                        tts_done = True
                    else:
                        for sse in self._handle_streaming_tts_event(tts_event):
                            yield sse
                    event = None
                elif kind == "audio_ready":
                    while True:
                        try:
                            yield audio_queue.get_nowait()
                        except QueueEmpty:
                            break
                    event = None
                else:
                    event = None

                if event is not None:
                    if event.type == "usage":
                        llm_usage = event.usage
                        continue
                    if event.type == "finish":
                        llm_finish_reason = event.finish_reason
                        continue
                    token = event.text
                    if not token:
                        continue
                    full_answer += token
                    sentence_buffer += token
                    if faq_documents is None:
                        yield StreamEvent(type="text_chunk", data={"token": token})

                    if streaming_requested:
                        if not tts_failed:
                            tts_text_buffer += token
                    elif faq_documents is None:
                        # HTTP TTS：句子级别缓冲
                        sentences, sentence_buffer = self._take_speakable_sentences(sentence_buffer)
                        for sentence in sentences:
                            if not request.text_only:
                                schedule_audio(sentence)

                        while True:
                            try:
                                yield audio_queue.get_nowait()
                            except QueueEmpty:
                                break

                if (
                    tts_connected
                    and not tts_failed
                    and tts_stream is not None
                    and self._should_flush_streaming_tts(tts_text_buffer)
                ):
                    chunk = tts_text_buffer
                    tts_text_buffer = ""
                    try:
                        await tts_stream.send_text(chunk)
                    except Exception:
                        logger.exception("Streaming TTS send failed; switching to HTTP fallback")
                        tts_failed = True
                        tts_done = True

                if llm_done and tts_connected and not tts_failed and not tts_finish_sent and tts_stream is not None:
                    try:
                        if tts_text_buffer:
                            await tts_stream.send_text(tts_text_buffer)
                            tts_text_buffer = ""
                        await tts_stream.finish()
                        tts_finish_requested.set()
                        tts_finish_sent = True
                    except Exception:
                        logger.exception("Streaming TTS finish failed; switching to HTTP fallback")
                        tts_failed = True
                        tts_done = True

                if llm_done and streaming_requested and not tts_connected and tts_failed:
                    tts_done = True
        except BaseException:
            await cancel_audio()
            raise
        finally:
            for task in (llm_task, tts_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (llm_task, tts_task) if task is not None),
                return_exceptions=True,
            )
            if tts_stream is not None:
                try:
                    await tts_stream.close()
                except Exception:
                    logger.exception("Failed to close streaming TTS session")

        if llm_error is not None:
            await cancel_audio()
            raise llm_error
        if visibility_changed:
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
            full_answer = polish_answer(faq_result.answer, request.persona, faq_sources)

        faq_text_sent = faq_documents is not None
        if faq_text_sent:
            yield StreamEvent(type="text", data={"text": full_answer, "is_complete": True})

        if faq_documents is not None and not request.text_only:
            if full_answer.strip():
                schedule_audio(full_answer.strip())
        elif streaming_requested and tts_failed and not request.text_only:
            remaining_text = full_answer[tts_confirmed_chars:].strip()
            if remaining_text:
                schedule_audio(remaining_text)
        elif not streaming_requested and sentence_buffer.strip() and not request.text_only:
            schedule_audio(sentence_buffer.strip())

        try:
            for task in audio_tasks:
                await task
                if not await self._epoch_is_current(request_epoch):
                    await cancel_audio()
                    yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
                    return
                while True:
                    try:
                        yield audio_queue.get_nowait()
                    except QueueEmpty:
                        break
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
            full_answer = polish_answer(faq_result.answer, request.persona, faq_sources)
        if not await self._epoch_is_current(request_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
            return
        if shared_cache_allowed and not degraded_llm:
            await self.qa_cache.set(cache_key, full_answer, sources, epoch=request_epoch)
        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await self._persist_interaction(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=full_answer,
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
            yield StreamEvent(type="text", data={"text": full_answer, "is_complete": not incomplete})
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

    @staticmethod
    def _take_speakable_sentences(buffer: str) -> tuple[list[str], str]:
        sentences: list[str] = []
        start = 0
        for index, char in enumerate(buffer):
            if char in "。！？!?；;\n" or (char in "，、," and index - start + 1 >= 8):
                sentence = buffer[start:index + 1].strip()
                if sentence:
                    sentences.append(sentence)
                start = index + 1
        return sentences, buffer[start:]

    @staticmethod
    def _should_flush_streaming_tts(buffer: str) -> bool:
        """以短语为单位发送，兼顾首音延迟、韵律和 WebSocket 帧数量。"""
        if not buffer:
            return False
        if buffer[-1] in "。！？!?；;\n":
            return True
        if buffer[-1] in "，、," and len(buffer) >= 8:
            return True
        return len(buffer) >= 16

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
        self, sentence: str, queue: asyncio.Queue[StreamEvent], *,
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
        await queue.put(StreamEvent(type="avatar", data={
            "viseme_text": avatar.viseme_text,
            "emotion": self._active_response_policy.avatar_emotion,
        }))
        await queue.put(
            self._build_audio_event(
                sentence,
                audio.base64_audio,
                audio.duration_ms,
                audio.provider,
            )
        )
        if notify is not None:
            await notify()

    @classmethod
    def _build_audio_event(
        cls,
        text: str,
        base64_audio: str,
        duration_ms: int,
        provider: str = "unknown",
    ) -> StreamEvent:
        safe_duration = max(duration_ms, int(len(text.replace(" ", "")) * 180), 800)
        return StreamEvent(
            type="audio",
            data={
                "base64": base64_audio,
                "duration_ms": safe_duration,
                "text": text,
                "provider": provider,
                "viseme_timeline": cls._build_viseme_timeline(text, safe_duration),
            },
        )

    @staticmethod
    def _build_viseme_timeline(text: str, duration_ms: int) -> list[dict]:
        """基于拼音的口型时间线——pypinyin 可用时走音素映射，否则走增强版降级。"""
        pinyin_fn = _get_pinyin()
        if pinyin_fn is not None:
            return build_viseme_timeline(text, duration_ms, pinyin_fn=pinyin_fn)
        return build_viseme_timeline_fallback(text, duration_ms)

    @staticmethod
    def _words_to_viseme_timeline(words: list[dict]) -> list[dict]:
        """将 TTS 字级别时间戳转换为 viseme 时间线（结合 pypinyin 开口度）。"""
        from app.services.avatar.viseme import (
            get_viseme_openness,
            get_viseme_roundness,
            get_duration_weight,
            is_closed_initial,
        )
        pinyin_fn = _get_pinyin()
        finals_style = _get_finals_style()
        timeline: list[dict] = []
        for word in words:
            char = word.get("text", "")
            begin = word.get("begin_time", 0)
            end = word.get("end_time", begin + 100)

            openness = 0.38  # 默认中等开口
            roundness = 0.15
            if pinyin_fn is not None and finals_style is not None and finals_style >= 0 and char and not char.isspace():
                final = ""
                try:
                    results = pinyin_fn(char, heteronym=False, style=finals_style)
                    if results:
                        final = str(results[0][0]) if isinstance(results[0], list) else str(results[0])
                except Exception:
                    pass
                if final:
                    openness = get_viseme_openness(final)
                    roundness = get_viseme_roundness(final)

            timeline.append({
                "start": begin,
                "end": end,
                "value": round(openness, 3),
                "form": round(roundness, 3),
            })
        return timeline

    def _handle_streaming_tts_event(self, tts_event) -> list[StreamEvent]:
        """将 StreamingTTSEvent 转换为 SSE StreamEvent 列表。"""
        results: list[StreamEvent] = []
        if tts_event.type == "audio_chunk":
            # PCM 音频块，base64 编码后下发
            b64 = base64.b64encode(tts_event.data).decode("ascii")
            results.append(StreamEvent(type="audio_chunk", data={
                "base64": b64,
                "sample_rate": tts_event.sample_rate,
                "channels": 1,
                "bits": 16,
            }))
        elif tts_event.type == "word_timestamps":
            # 字级别时间戳 → viseme 时间线 + 原始逐字时间（前端字幕逐字同步用）
            timestamp_data = tts_event.data if isinstance(tts_event.data, dict) else {"words": tts_event.data}
            raw_words = timestamp_data.get("words", [])
            viseme_timeline = self._words_to_viseme_timeline(raw_words)
            if viseme_timeline:
                results.append(StreamEvent(type="audio_chunk", data={
                    "viseme_timeline": viseme_timeline,
                    "sentence_index": timestamp_data.get("sentence_index", 0),
                    "word_timeline": [
                        {
                            "text": word.get("text", ""),
                            "begin_time": word.get("begin_time", 0),
                            "end_time": word.get("end_time", 0),
                        }
                        for word in raw_words
                    ],
                }))
        elif tts_event.type == "sentence_begin":
            # 通知前端新句子开始
            results.append(StreamEvent(type="avatar", data={
                "viseme_text": tts_event.data,
                "emotion": self._active_response_policy.avatar_emotion,
            }))
        return results

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
    def _doc_to_source(document: RetrievedDocument, *, evidence_id: str) -> dict:
        return {
            "evidence_id": evidence_id,
            "title": document.title,
            "snippet": document.snippet,
            "source": document.source,
            "score": document.score,
            "entry_id": document.entry_id,
            "revision_id": document.revision_id,
            "chunk_id": document.chunk_id,
        }

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
