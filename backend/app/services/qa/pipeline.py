from __future__ import annotations

import asyncio
import base64
import logging
import re
from asyncio import QueueEmpty
from time import perf_counter
import json

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
from app.schemas.chat import ChatRequest, ConversationContext
from app.services.avatar.base import BaseAvatarService
from app.services.avatar.viseme import build_viseme_timeline, build_viseme_timeline_fallback
from app.services.coze.client import CozeRoutePlan, CozeRoutePlanner, CozeRoutePlannerError
from app.services.llm.base import BaseLLMService
from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.live_data.service import LiveDataService
from app.services.emotion import (
    EmotionLabel,
    MultimodalEmotionFusion,
    TextEmotionAnalyzer,
    apply_answer_prefix,
    audio_emotion_signal,
    response_policy_for,
)
from app.services.qa.cache import QACache
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import (
    GuidedSelectionResolver,
    ResolvedInteraction,
    build_selection_cache_key,
)
from app.services.qa.intent_router import IntentRouter
from app.services.qa.stream_events import StreamEvent
from app.services.qa.answer_styler import polish_answer, no_evidence_reply
from app.services.rag.base import BaseRAGService, RetrievedDocument, RetrievalScope
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.base import BaseTTSService
from app.services.tts.streaming import StreamingTTSService, StreamingTTSSession

logger = logging.getLogger(__name__)

_LINGSHAN_ATTRACTIONS = [
    "灵山大佛", "大佛", "灵山梵宫", "梵宫", "九龙灌浴", "五印坛城",
    "坛城", "五明桥", "五智门", "五灯湖", "佛教文化博览馆", "佛足坛",
    "拈花堂", "拈花广场", "无尽意斋", "曼飞龙塔", "梵天花海",
    "大照壁", "灵山大照壁", "百子戏弥勒", "祥符禅寺",
    "菩提大道", "阿育王柱", "降魔浮雕", "香月花街", "鹿鸣谷",
    "灵山胜境", "灵山",
]

_PERSONA_AUDIENCE_MAP = {
    "hanfu": "culture",
    "monk": "culture",
    "modern": "free",
}

_TOPIC_AUDIENCE_HINTS = {
    "family": "family",
    "blessing": "culture",
    "history": "culture",
    "architecture": "culture",
    "routes": "free",
    "dining": "leisure",
    "practical": "general",
}


def _infer_audience_type(request: ChatRequest) -> str:
    selection = request.selection
    if selection is not None:
        if selection.audience_type:
            return selection.audience_type
        if selection.mode == "topic" and selection.topic_key:
            return _TOPIC_AUDIENCE_HINTS.get(selection.topic_key, "general")
    if request.persona:
        return _PERSONA_AUDIENCE_MAP.get(request.persona, "general")
    return "general"


def _extract_interests(request: ChatRequest) -> list[str]:
    interests: list[str] = []
    selection = request.selection
    if selection is not None and selection.interests:
        interests.extend(selection.interests)
    query = request.query
    for attraction in _LINGSHAN_ATTRACTIONS:
        if attraction in query and attraction not in interests:
            interests.append(attraction)
    return interests[:8]


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
        streaming_tts_service: StreamingTTSService | None = None,
        chat_log_repository: ChatLogRepository,
        visitor_repository: VisitorRepository | None = None,
        guided_selector: GuidedSelectionResolver,
        followup_suggestions: FollowUpSuggestionService,
        blind_spot_tracker: BlindSpotTracker | None = None,
        answer_cache_namespace: str = "default",
        intent_router: IntentRouter | None = None,
        live_data_service: LiveDataService | None = None,
        coze_route_planner: CozeRoutePlanner | None = None,
        knowledge_repository: KnowledgeRepository | None = None,
        route_repository: RouteRepository | None = None,
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
        self.guided_selector = guided_selector
        self.followup_suggestions = followup_suggestions
        self.blind_spot_tracker = blind_spot_tracker
        self.answer_cache_namespace = answer_cache_namespace
        self.intent_router = intent_router or IntentRouter()
        self.live_data_service = live_data_service
        self.coze_route_planner = coze_route_planner
        self.knowledge_repository = knowledge_repository
        self.route_repository = route_repository
        self.text_emotion_analyzer = TextEmotionAnalyzer()
        self.emotion_fusion = MultimodalEmotionFusion()
        self._active_emotion = self.emotion_fusion.fuse(None, None)
        self._active_response_policy = response_policy_for(self._active_emotion)
        self._active_text_emotion = None
        self._active_audio_emotion = None

    async def stream_chat(self, request: ChatRequest):
        start = perf_counter()
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

        # 视觉识别线索注入：用 Qwen 识别出的候选景点限定 RAG 检索范围
        vision = request.vision_context
        if vision is not None and vision.candidate_attractions and (resolved.scope is None or resolved.scope.is_empty()):
            vision_attraction = await self.guided_selector.find_attraction_by_candidates(vision.candidate_attractions)
            if vision_attraction is not None:
                resolved = ResolvedInteraction(
                    selection=resolved.selection,
                    scope=RetrievalScope(source_entry_id=vision_attraction.id),
                    resolution_source="selection",
                    active_subject=vision_attraction.title,
                    warnings=resolved.warnings,
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

        rewrite_context = request.context
        if resolved.active_subject:
            rewrite_context = ConversationContext(
                last_subject=resolved.active_subject,
                history_summary=request.context.history_summary if request.context else None,
            )
        normalized_query = self.query_rewriter.rewrite(request.query, rewrite_context)
        intent_decision = self.intent_router.detect(request.query, resolved.selection)
        yield StreamEvent(
            type="intent",
            data={
                "intent": intent_decision.intent,
                "confidence": intent_decision.confidence,
                "matched_keywords": list(intent_decision.matched_keywords),
            },
        )

        if self._should_use_dynamic_route(intent_decision, request):
            print(f"[PIPELINE] dynamic route triggered, intent={intent_decision.intent}, calling Coze...", flush=True)
            yield StreamEvent(type="status", data={"text": "创意路线私人定制中，用时可能较长，请稍等..."})
            dynamic_plan = await self._try_dynamic_route(
                request=request,
                normalized_query=normalized_query,
                resolved=resolved,
                start=start,
            )
            print(f"[PIPELINE] dynamic_plan is {'NOT None' if dynamic_plan is not None else 'None'}", flush=True)
            if dynamic_plan is not None:
                async for event in self._emit_dynamic_route_answer(
                    request=request,
                    normalized_query=normalized_query,
                    plan=dynamic_plan,
                    start=start,
                    resolved=resolved,
                ):
                    yield event
                return
            print("[PIPELINE] Coze failed, falling through to static_route", flush=True)

        if intent_decision.intent in {"dynamic_route", "static_route"}:
            static_route = await self._build_static_route_answer(request.query)
            if static_route is not None:
                answer, route_sources = static_route
                yield StreamEvent(type="status", data={"text": "正在整理游览路线..."})
                async for event in self._emit_final_answer(
                    request=request,
                    normalized_query=normalized_query,
                    answer=answer,
                    sources=route_sources,
                    hit_level="static_route",
                    start=start,
                    resolved=resolved,
                ):
                    yield event
                return
        cache_key = build_selection_cache_key(
            normalized_query,
            resolved.selection,
            answer_namespace=self.answer_cache_namespace,
        )
        yield StreamEvent(type="status", data={"text": "正在查找答案..."})

        faq_result = self.faq_matcher.match(normalized_query)
        if faq_result.is_hit:
            sources = [
                {
                    "evidence_id": f"证据{index}",
                    "title": "FAQ",
                    "snippet": faq_result.answer[:80],
                    "source": source,
                }
                for index, source in enumerate(faq_result.sources, start=1)
            ]
            styled_answer = polish_answer(faq_result.answer, request.persona, sources)
            async for event in self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=styled_answer,
                sources=sources,
                hit_level=f"faq_{faq_result.level}",
                start=start,
                resolved=resolved,
            ):
                yield event
            return

        cached = await self.qa_cache.get(cache_key)
        if cached:
            styled_answer = polish_answer(cached.answer, request.persona, cached.sources)
            async for event in self._emit_final_answer(
                request=request,
                normalized_query=normalized_query,
                answer=styled_answer,
                sources=cached.sources,
                hit_level="cache",
                start=start,
                resolved=resolved,
            ):
                yield event
            return

        yield StreamEvent(type="status", data={"text": "正在检索景区知识..."})
        documents = await self.rag_service.retrieve(
            request.query,
            normalized_query=normalized_query,
            scope=resolved.scope,
        )
        sources = [
            self._doc_to_source(document, evidence_id=f"证据{index}")
            for index, document in enumerate(documents, start=1)
        ]
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})

        if not documents:
            if self.blind_spot_tracker is not None:
                try:
                    await self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="rag_no_docs",
                )
                    logger.info("Blind spot recorded (RAG no docs): %s", normalized_query)
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
            ):
                yield event
            return

        full_answer = ""
        sentence_buffer = ""
        llm_usage = LLMUsage()
        llm_finish_reason: str | None = None
        audio_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        audio_tasks: list[asyncio.Task[None]] = []

        # ── 流式 TTS 路径 ──
        tts_stream: StreamingTTSSession | None = None
        streaming_requested = (
            self.streaming_tts_service is not None
            and not request.text_only
        )
        if streaming_requested and self.streaming_tts_service is not None:
            tts_stream = self.streaming_tts_service.create_session()

        mux_queue: asyncio.Queue[tuple[str, object | None]] = asyncio.Queue()
        tts_finish_requested = asyncio.Event()

        async def produce_llm_events() -> None:
            try:
                async for item in self.llm_service.stream_generate(
                    self._emotion_aware_query(request.query),
                    documents,
                    persona=request.persona,
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
        llm_error: Exception | None = None
        tts_connected = False
        tts_done = not streaming_requested
        tts_failed = False
        tts_finish_sent = False
        tts_text_buffer = ""
        tts_confirmed_chars = 0

        try:
            while not llm_done or not tts_done:
                kind, payload = await mux_queue.get()

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
                    yield StreamEvent(type="text_chunk", data={"token": token})

                    if streaming_requested:
                        if not tts_failed:
                            tts_text_buffer += token
                    else:
                        # HTTP TTS：句子级别缓冲
                        if self._should_trigger_tts(token, sentence_buffer):
                            sentence = sentence_buffer.strip()
                            sentence_buffer = ""
                            if sentence and not request.text_only:
                                audio_tasks.append(asyncio.create_task(self._queue_audio(sentence, audio_queue)))

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
            raise llm_error

        if streaming_requested and tts_failed and not request.text_only:
            remaining_text = full_answer[tts_confirmed_chars:].strip()
            if remaining_text:
                audio_tasks.append(asyncio.create_task(self._queue_audio(remaining_text, audio_queue)))
        elif not streaming_requested and sentence_buffer.strip() and not request.text_only:
            audio_tasks.append(asyncio.create_task(self._queue_audio(sentence_buffer.strip(), audio_queue)))

        for task in audio_tasks:
            await task
            while True:
                try:
                    yield audio_queue.get_nowait()
                except QueueEmpty:
                    break

        degraded_llm = bool(
            llm_finish_reason
            and (
                llm_finish_reason.startswith("fallback_")
                or llm_finish_reason.startswith("interrupted_")
            )
        )
        if degraded_llm and self.blind_spot_tracker is not None:
            try:
                await self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="llm_fallback",
                )
                logger.info("Blind spot recorded (LLM degraded): %s", normalized_query)
            except Exception:
                logger.exception("Knowledge blind spot recording failed")
        if not degraded_llm and self._active_emotion.label == EmotionLabel.NEUTRAL:
            await self.qa_cache.set(cache_key, full_answer, sources)
        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await self._persist_interaction(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=full_answer,
            sources=sources,
            hit_level="rag_llm_fallback" if degraded_llm else "rag",
            latency_ms=latency_ms,
            request=request,
        )
        logger.info(
            "LLM completed: finish_reason=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s cached_tokens=%s",
            llm_finish_reason,
            llm_usage.prompt_tokens,
            llm_usage.completion_tokens,
            llm_usage.total_tokens,
            llm_usage.cached_tokens,
        )
        yield StreamEvent(type="text", data={"text": full_answer, "is_complete": True})
        yield self._followup_event(resolved)
        yield self._done_event(
            chat_log_id=chat_log_id,
            hit_level="rag_llm_fallback" if degraded_llm else "rag",
            total_ms=latency_ms,
            degraded=degraded_llm,
            provider="deepseek" if not degraded_llm else "evidence_fallback",
        )

    async def _build_static_route_answer(self, query: str) -> tuple[str, list[dict]] | None:
        """Return a grounded route when the optional dynamic planner is unavailable."""
        if self.route_repository is None:
            return None

        routes = await self.route_repository.list_all()
        if not routes:
            return None

        def pick(*keywords: str):
            return next(
                (
                    route
                    for route in routes
                    if any(keyword in route.title or keyword in getattr(route, "tags", "") for keyword in keywords)
                ),
                None,
            )

        normalized = (query or "").strip()
        is_point_to_point = (
            "大佛" in normalized
            and "梵宫" in normalized
            and any(marker in normalized for marker in ("怎么走", "怎么去", "从", "到"))
        )
        if is_point_to_point:
            selected = next(
                (route for route in routes if "大佛" in route.route_plan and "梵宫" in route.route_plan),
                routes[0],
            )
            answer = (
                "从灵山大佛到灵山梵宫，建议沿景区主游线按现场导视前往："
                "灵山大佛 → 灵山梵宫。"
                "这段为园内步行路线；如需少走路，可在出发前向服务台确认当日摆渡安排。"
            )
        else:
            selected = None
            if any(marker in normalized for marker in ("小孩", "孩子", "亲子")):
                selected = pick("亲子")
            elif any(marker in normalized for marker in ("建筑", "佛教", "文化", "朝圣")):
                selected = pick("历史", "文化")
            elif any(marker in normalized for marker in ("自然", "风景", "免费")):
                selected = pick("自然")
            elif any(marker in normalized for marker in ("老人", "省力", "半天", "3个小时", "三个小时")):
                selected = pick("亲子", "自然")
            selected = selected or routes[0]

            route_plan = selected.route_plan
            if any(marker in normalized for marker in ("3个小时", "三个小时")):
                stops = [item.strip() for item in route_plan.split("→") if item.strip()]
                route_plan = " → ".join(stops[:4])
                answer = (
                    f"推荐3小时精华路线：{route_plan}。"
                    "时间紧时优先看核心景点，其余景点可根据现场时间灵活取舍。"
                )
            elif "半天" in normalized:
                answer = (
                    f"半天可参考{selected.title}（{selected.duration_label}）：{route_plan}。"
                    "建议提前入园，并按现场演出时间和体力情况删减停留点。"
                )
            elif "一日" in normalized or "全天" in normalized:
                answer = (
                    f"一日游建议以{selected.title}为主线：{route_plan}。"
                    "上午安排核心景点，下午可继续游览梵宫、五印坛城等文化建筑，并预留休息与用餐时间。"
                )
            else:
                answer = f"推荐{selected.title}（{selected.duration_label}）：{route_plan}。"

        sources = [{
            "evidence_id": "路线1",
            "title": selected.title,
            "snippet": selected.route_plan,
            "source": selected.source,
        }]
        return answer, sources
    def _should_use_dynamic_route(self, intent_decision, request: ChatRequest) -> bool:
        if not intent_decision.is_dynamic_route:
            return False
        if self.live_data_service is None or self.coze_route_planner is None:
            return False
        if not self.coze_route_planner.is_configured:
            return False
        return request.selection is not None or any(
            marker in request.query for marker in ("路线", "线路", "怎么逛", "推荐")
        )

    async def _try_dynamic_route(
        self,
        *,
        request: ChatRequest,
        normalized_query: str,
        resolved: ResolvedInteraction,
        start: float,
    ) -> CozeRoutePlan | None:
        del normalized_query, start
        if (
            self.knowledge_repository is None
            or self.route_repository is None
            or self.live_data_service is None
            or self.coze_route_planner is None
        ):
            return None

        attractions = await self.knowledge_repository.list_by_category("景点信息")
        routes = await self.route_repository.list_all()
        if not attractions or not routes:
            return None

        live_context = self.live_data_service.build_context(attractions)
        payload = {
            "question": request.query,
            "visitor_profile_json": json.dumps(
                self._build_visitor_profile(request, resolved),
                ensure_ascii=False,
            ),
            "route_candidates_json": json.dumps(
                self._build_route_candidates(routes, attractions),
                ensure_ascii=False,
            ),
            "live_context_json": json.dumps(
                live_context.model_dump(mode="json"),
                ensure_ascii=False,
            ),
            "allowed_attraction_ids_json": json.dumps([str(item.id) for item in attractions], ensure_ascii=False),
        }
        try:
            print("[PIPELINE] calling coze_route_planner.run()...", flush=True)
            plan = await self.coze_route_planner.run(payload)
            print(f"[PIPELINE] Coze returned plan with {len(plan.route_stops)} stops", flush=True)
            self._validate_route_stop_ids(plan, payload["allowed_attraction_ids_json"])
            return plan
        except CozeRoutePlannerError as e:
            print(f"[PIPELINE] CozeRoutePlannerError: {e}", flush=True)
            logger.exception("Dynamic route planning failed; fallback to static QA.")
            return None
        except Exception as e:
            print(f"[PIPELINE] Unexpected error in Coze: {type(e).__name__}: {e}", flush=True)
            logger.exception("Unexpected error in dynamic route planning.")
            return None

    async def _emit_dynamic_route_answer(
        self,
        *,
        request: ChatRequest,
        normalized_query: str,
        plan: CozeRoutePlan,
        start: float,
        resolved: ResolvedInteraction,
    ):
        answer = apply_answer_prefix(plan.answer.strip(), self._active_response_policy)
        if plan.warning:
            answer = f"{answer}\n\n提示：{plan.warning}"
        if plan.adjustments:
            answer = f"{answer}\n\n调整依据：{'；'.join(plan.adjustments)}"

        sources = [
            {
                "evidence_id": f"动态{index}",
                "title": source,
                "snippet": source,
                "source": "coze_dynamic_route",
            }
            for index, source in enumerate(plan.sources or ["官方路线候选", "实时上下文"], start=1)
        ]
        answer = self._ensure_inline_citations(answer, sources)
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})

        if request.text_only:
            yield StreamEvent(type="text", data={"text": answer, "is_complete": True})
        else:
            audio_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
            audio_tasks: list[asyncio.Task[None]] = []
            sentence_buffer = ""

            for char in answer:
                sentence_buffer += char
                yield StreamEvent(type="text_chunk", data={"token": char})

                if self._should_trigger_tts(char, sentence_buffer):
                    sentence = sentence_buffer.strip()
                    sentence_buffer = ""
                    if sentence:
                        audio_tasks.append(asyncio.create_task(self._queue_audio(sentence, audio_queue)))

                while True:
                    try:
                        yield audio_queue.get_nowait()
                    except QueueEmpty:
                        break

            if sentence_buffer.strip():
                audio_tasks.append(asyncio.create_task(self._queue_audio(sentence_buffer.strip(), audio_queue)))

            for task in audio_tasks:
                await task
                while True:
                    try:
                        yield audio_queue.get_nowait()
                    except QueueEmpty:
                        break

            yield StreamEvent(type="text", data={"text": answer, "is_complete": True})

        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await self._persist_interaction(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level="dynamic_route_coze",
            latency_ms=latency_ms,
            request=request,
        )
        yield self._followup_event(resolved)
        yield self._done_event(
            chat_log_id=chat_log_id,
            hit_level="dynamic_route_coze",
            total_ms=latency_ms,
            provider="coze",
        )

    @staticmethod
    def _should_trigger_tts(token: str, buffer: str) -> bool:
        if token in "。！？!?":
            return True
        if token in "，、" and len(buffer) >= 8:
            return True
        return False

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

    @staticmethod
    def _build_visitor_profile(request: ChatRequest, resolved: ResolvedInteraction) -> dict:
        selection = request.selection
        return {
            "audience_type": selection.audience_type if selection else None,
            "available_hours": selection.available_hours if selection else None,
            "avoid_crowded": selection.avoid_crowded if selection else None,
            "interests": selection.interests if selection else [],
            "active_subject": resolved.active_subject,
            "input_mode": request.input_mode,
        }

    def _build_route_candidates(self, routes, attractions) -> dict:
        return {
            "routes": [
                {
                    "id": route.id,
                    "name": route.title,
                    "duration": route.duration_label,
                    "route_plan": route.route_plan,
                    "stops": self._extract_route_stops(route.route_plan, attractions),
                }
                for route in routes
            ]
        }

    @staticmethod
    def _extract_route_stops(route_plan: str, attractions) -> list[dict]:
        stops: list[dict] = []
        for attraction in attractions:
            aliases = [item.strip() for item in attraction.aliases.split("|") if item.strip()]
            terms = [attraction.title, *aliases]
            if any(term and term in route_plan for term in terms):
                stops.append({"attraction_id": str(attraction.id), "name": attraction.title})
        return stops

    @staticmethod
    def _validate_route_stop_ids(plan: CozeRoutePlan, allowed_ids_json: str) -> None:
        allowed_ids = set(json.loads(allowed_ids_json))
        for stop in plan.route_stops:
            attraction_id = str(stop.get("attraction_id", "")).strip()
            if attraction_id and attraction_id not in allowed_ids:
                raise CozeRoutePlannerError(f"Unexpected attraction id from Coze: {attraction_id}")

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
    ):
        answer = apply_answer_prefix(answer, self._active_response_policy)
        answer = self._ensure_inline_citations(answer, sources)
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})
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
        )
        yield self._followup_event(resolved)
        yield self._done_event(
            chat_log_id=chat_log_id,
            hit_level=hit_level,
            total_ms=latency_ms,
            degraded=hit_level in {"rag_insufficient", "rag_llm_fallback"},
            provider="local" if hit_level.startswith("faq_") or hit_level == "cache" else "rag",
        )

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
        return log.id

    @staticmethod
    def _done_event(
        *,
        chat_log_id: int,
        hit_level: str,
        total_ms: int,
        degraded: bool = False,
        provider: str = "local",
    ) -> StreamEvent:
        return StreamEvent(
            type="done",
            data={
                "chat_log_id": chat_log_id,
                "hit_level": hit_level,
                "total_ms": total_ms,
                "degraded": degraded,
                "provider": provider,
            },
        )

    async def _queue_audio(self, sentence: str, queue: asyncio.Queue[StreamEvent]) -> None:
        audio = await self.tts_service.synthesize(sentence)
        avatar = await self.avatar_service.drive(sentence)
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
                "sample_rate": 24000,
                "channels": 1,
                "bits": 16,
            }))
        elif tts_event.type == "word_timestamps":
            # 字级别时间戳 → viseme 时间线
            timestamp_data = tts_event.data if isinstance(tts_event.data, dict) else {"words": tts_event.data}
            viseme_timeline = self._words_to_viseme_timeline(timestamp_data.get("words", []))
            if viseme_timeline:
                results.append(StreamEvent(type="audio_chunk", data={
                    "viseme_timeline": viseme_timeline,
                    "sentence_index": timestamp_data.get("sentence_index", 0),
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
        }

    @staticmethod
    def _coerce_llm_event(item: LLMStreamEvent | str) -> LLMStreamEvent:
        if isinstance(item, LLMStreamEvent):
            return item
        return LLMStreamEvent(type="content", text=str(item))

    @staticmethod
    def _ensure_inline_citations(answer: str, sources: list[dict]) -> str:
        if "[证据" in answer or "[璇佹嵁" in answer or not sources:
            return answer
        evidence_ids = [
            str(source.get("evidence_id", "")).strip()
            for source in sources
            if str(source.get("evidence_id", "")).strip()
        ]
        if not evidence_ids:
            return answer
        return f"{answer}{''.join(f'[{evidence_id}]' for evidence_id in evidence_ids)}"

    def _followup_event(self, resolved: ResolvedInteraction) -> StreamEvent:
        return StreamEvent(
            type="followups",
            data={"items": self.followup_suggestions.generate(resolved)},
        )
