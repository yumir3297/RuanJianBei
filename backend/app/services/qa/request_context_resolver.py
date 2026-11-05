from __future__ import annotations

import logging
from dataclasses import dataclass

from app.repositories.visitor_memory import VisitorMemoryRepository
from app.schemas.chat import ChatRequest
from app.services.emotion import (
    EmotionResponsePolicy,
    EmotionSignal,
    FusedEmotion,
    MultimodalEmotionFusion,
    TextEmotionAnalyzer,
    audio_emotion_signal,
    response_policy_for,
)
from app.services.memory.profile import build_memory_prompt
from app.services.qa.guided_selector import GuidedSelectionResolver, ResolvedInteraction
from app.services.qa.intent_router import IntentDecision, IntentRouter
from app.services.qa.request_profile import resolve_narration_audience
from app.services.qa.request_query_context import RequestQueryContext, resolve_request_query_context
from app.services.qa.vision_evidence import resolve_vision_evidence
from app.services.rag.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RequestContextResolution:
    text_emotion: EmotionSignal | None
    audio_emotion: EmotionSignal | None
    fused_emotion: FusedEmotion
    response_policy: EmotionResponsePolicy
    resolved: ResolvedInteraction
    audience: str | None
    memory_prompt: str | None
    confirmed_visual_title: str | None
    query_context: RequestQueryContext | None
    error_code: str | None = None
    error_message: str | None = None


class RequestContextResolver:
    """Prepare one request's selection, emotion, memory, vision, and query context."""

    def __init__(
        self,
        *,
        guided_selector: GuidedSelectionResolver,
        query_rewriter: QueryRewriter,
        intent_router: IntentRouter,
        visitor_memory_repository: VisitorMemoryRepository | None,
        vision_catalog,
        vision_site_id: str | None,
        text_emotion_analyzer: TextEmotionAnalyzer | None = None,
        emotion_fusion: MultimodalEmotionFusion | None = None,
        vision_evidence_resolver=resolve_vision_evidence,
    ) -> None:
        self.guided_selector = guided_selector
        self.query_rewriter = query_rewriter
        self.intent_router = intent_router
        self.visitor_memory_repository = visitor_memory_repository
        self.vision_catalog = vision_catalog
        self.vision_site_id = vision_site_id
        self.text_emotion_analyzer = text_emotion_analyzer or TextEmotionAnalyzer()
        self.emotion_fusion = emotion_fusion or MultimodalEmotionFusion()
        self.vision_evidence_resolver = vision_evidence_resolver or resolve_vision_evidence

    async def resolve(self, request: ChatRequest) -> RequestContextResolution:
        text_emotion = self.text_emotion_analyzer.analyze(request.query)
        audio_emotion = None
        if request.emotion_context is not None:
            audio_emotion = audio_emotion_signal(
                request.emotion_context.audio_emotion,
                request.emotion_context.audio_confidence,
                source=request.emotion_context.audio_source or "audio",
            )
        fused_emotion = self.emotion_fusion.fuse(text_emotion, audio_emotion)
        response_policy = response_policy_for(fused_emotion)

        resolved = await self.guided_selector.resolve(request.query, request.selection, request.context)
        if (
            request.selection
            and request.selection.attraction_id is not None
            and "invalid_attraction_id" in resolved.warnings
        ):
            return RequestContextResolution(
                text_emotion=text_emotion,
                audio_emotion=audio_emotion,
                fused_emotion=fused_emotion,
                response_policy=response_policy,
                resolved=resolved,
                audience=None,
                memory_prompt=None,
                confirmed_visual_title=None,
                query_context=None,
                error_code="attraction_selection_stale",
                error_message="所选景点已不可用或更新，请重新选择。",
            )

        audience = resolve_narration_audience(request)
        memory_prompt = await self._visitor_memory_prompt(request)
        vision_evidence = await self.vision_evidence_resolver(
            request.vision_context,
            resolved,
            vision_catalog=self.vision_catalog,
            vision_site_id=self.vision_site_id,
        )
        if vision_evidence.error_code is not None:
            return RequestContextResolution(
                text_emotion=text_emotion,
                audio_emotion=audio_emotion,
                fused_emotion=fused_emotion,
                response_policy=response_policy,
                resolved=vision_evidence.resolved,
                audience=audience,
                memory_prompt=memory_prompt,
                confirmed_visual_title=None,
                query_context=None,
                error_code=vision_evidence.error_code,
                error_message=vision_evidence.error_message,
            )

        resolved = vision_evidence.resolved
        query_context = resolve_request_query_context(
            request,
            resolved,
            vision=request.vision_context,
            query_rewriter=self.query_rewriter,
            intent_router=self.intent_router,
        )
        return RequestContextResolution(
            text_emotion=text_emotion,
            audio_emotion=audio_emotion,
            fused_emotion=fused_emotion,
            response_policy=response_policy,
            resolved=resolved,
            audience=audience,
            memory_prompt=memory_prompt,
            confirmed_visual_title=vision_evidence.confirmed_title,
            query_context=query_context,
        )

    async def _visitor_memory_prompt(self, request: ChatRequest) -> str | None:
        if self.visitor_memory_repository is None or not request.visitor_id:
            return None
        try:
            memory = await self.visitor_memory_repository.get(request.visitor_id)
            if memory is None:
                return None
            return build_memory_prompt(VisitorMemoryRepository.decode(memory)) or None
        except Exception:
            logger.exception("Visitor memory read failed; continuing without memory.")
            return None
