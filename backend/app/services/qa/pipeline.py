from __future__ import annotations

import asyncio
import logging
import re
from asyncio import QueueEmpty
from time import perf_counter
import json

# ── 拼音导入缓存 ──
_PINYIN_FN = None
_PINYIN_CHECKED = False


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

    async def stream_chat(self, request: ChatRequest):
        start = perf_counter()
        resolved = self.guided_selector.resolve(request.query, request.selection, request.context)

        # 视觉识别线索注入：用 Qwen 识别出的候选景点限定 RAG 检索范围
        vision = request.vision_context
        if vision is not None and vision.candidate_attractions and (resolved.scope is None or resolved.scope.is_empty()):
            vision_attraction = self.guided_selector.find_attraction_by_candidates(vision.candidate_attractions)
            if vision_attraction is not None:
                resolved = ResolvedInteraction(
                    selection=resolved.selection,
                    scope=RetrievalScope(source_entry_id=vision_attraction.id),
                    resolution_source="selection",
                    active_subject=vision_attraction.title,
                    warnings=resolved.warnings,
                )

        yield StreamEvent(type="context", data=resolved.to_event_data())

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
            yield StreamEvent(type="status", data={"text": "正在规划个性化路线..."})
            dynamic_plan = await self._try_dynamic_route(
                request=request,
                normalized_query=normalized_query,
                resolved=resolved,
                start=start,
            )
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

        cached = self.qa_cache.get(cache_key)
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
                    self.blind_spot_tracker.record(
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

        async for stream_item in self.llm_service.stream_generate(
            request.query, documents, persona=request.persona,
        ):
            event = self._coerce_llm_event(stream_item)
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

            if token in "。！？!?":
                sentence = sentence_buffer.strip()
                sentence_buffer = ""
                if sentence and not request.text_only:
                    audio_tasks.append(asyncio.create_task(self._queue_audio(sentence, audio_queue)))

            while True:
                try:
                    yield audio_queue.get_nowait()
                except QueueEmpty:
                    break

        if sentence_buffer.strip() and not request.text_only:
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
                self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="llm_fallback",
                )
                logger.info("Blind spot recorded (LLM degraded): %s", normalized_query)
            except Exception:
                logger.exception("Knowledge blind spot recording failed")
        if not degraded_llm:
            self.qa_cache.set(cache_key, full_answer, sources)
        latency_ms = int((perf_counter() - start) * 1000)
        self.chat_log_repository.create(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=full_answer,
            sources=sources,
            hit_level="rag_llm_fallback" if degraded_llm else "rag",
            latency_ms=latency_ms,
        )
        if self.visitor_repository is not None:
            try:
                self.visitor_repository.upsert(
                    session_id=request.session_id,
                    interests=_extract_interests(request),
                    audience_type=_infer_audience_type(request),
                )
            except Exception:
                logger.exception("Visitor profile update failed.")
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
        yield StreamEvent(type="done", data={})

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

        attractions = self.knowledge_repository.list_by_category("景点信息")
        routes = self.route_repository.list_all()
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
            plan = await self.coze_route_planner.run(payload)
            self._validate_route_stop_ids(plan, payload["allowed_attraction_ids_json"])
            return plan
        except CozeRoutePlannerError:
            logger.exception("Dynamic route planning failed; fallback to static QA.")
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
        answer = plan.answer.strip()
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
        async for event in self._emit_final_answer(
            request=request,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level="dynamic_route_coze",
            start=start,
            resolved=resolved,
        ):
            yield event

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
        answer = self._ensure_inline_citations(answer, sources)
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})
        yield StreamEvent(type="text", data={"text": answer, "is_complete": True})
        if not request.text_only:
            audio = await self.tts_service.synthesize(answer)
            avatar = await self.avatar_service.drive(answer)
            emotion = self._answer_emotion(hit_level, len(sources))
            yield StreamEvent(type="avatar", data={"viseme_text": avatar.viseme_text, "emotion": emotion})
            yield self._build_audio_event(
                answer,
                audio.base64_audio,
                audio.duration_ms,
                audio.provider,
            )

        latency_ms = int((perf_counter() - start) * 1000)
        self.chat_log_repository.create(
            session_id=request.session_id,
            raw_query=request.query,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            latency_ms=latency_ms,
        )
        if self.visitor_repository is not None:
            try:
                self.visitor_repository.upsert(
                    session_id=request.session_id,
                    interests=_extract_interests(request),
                    audience_type=_infer_audience_type(request),
                )
            except Exception:
                logger.exception("Visitor profile update failed.")
        yield self._followup_event(resolved)
        yield StreamEvent(type="done", data={})

    async def _queue_audio(self, sentence: str, queue: asyncio.Queue[StreamEvent]) -> None:
        audio = await self.tts_service.synthesize(sentence)
        avatar = await self.avatar_service.drive(sentence)
        await queue.put(StreamEvent(type="avatar", data={"viseme_text": avatar.viseme_text, "emotion": avatar.emotion}))
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
    def _answer_emotion(hit_level: str | None, source_count: int) -> str:
        """根据回答路径决定数字人情感"""
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
