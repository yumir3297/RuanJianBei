from types import SimpleNamespace

import pytest

from app.schemas.chat import ChatRequest, EmotionContext, VisionContext
from app.schemas.selection import SelectionContext
from app.services.emotion import EmotionLabel, EmotionSignal, FusedEmotion, response_policy_for
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.intent_router import IntentDecision


def _resolver_type():
    from app.services.qa.request_context_resolver import RequestContextResolver

    return RequestContextResolver


class Analyzer:
    def analyze(self, query):
        return EmotionSignal(EmotionLabel.CONFUSED, 0.8, 0.6, "text")


class Fusion:
    def fuse(self, text_signal, audio_signal):
        assert text_signal.label == EmotionLabel.CONFUSED
        return FusedEmotion(EmotionLabel.CONFUSED, 0.8, 0.6, ("text",))


class GuidedSelector:
    def __init__(self, resolved):
        self.resolved = resolved
        self.calls = []

    async def resolve(self, query, selection, context):
        self.calls.append((query, selection, context))
        return self.resolved


class QueryRewriter:
    def __init__(self):
        self.calls = []

    def rewrite(self, query, context):
        self.calls.append((query, context))
        return f"normalized:{query}"


class IntentRouter:
    def __init__(self):
        self.calls = []

    def detect(self, query, selection):
        self.calls.append((query, selection))
        return IntentDecision("static_route", 0.9, ("路线",))


def _resolved(*, warnings=()):
    return ResolvedInteraction(
        selection=SelectionContext(mode="attraction", attraction_id=5),
        scope=None,
        resolution_source="selection",
        active_subject="旧景点",
        warnings=warnings,
    )


def _resolver(*, resolved=None, memory_repository=None, vision_resolver=None):
    selector = GuidedSelector(resolved or _resolved())
    rewriter = QueryRewriter()
    intent_router = IntentRouter()
    resolver = _resolver_type()(
        guided_selector=selector,
        query_rewriter=rewriter,
        intent_router=intent_router,
        visitor_memory_repository=memory_repository,
        vision_catalog=None,
        vision_site_id=None,
        text_emotion_analyzer=Analyzer(),
        emotion_fusion=Fusion(),
        vision_evidence_resolver=vision_resolver,
    )
    return resolver, selector, rewriter, intent_router


@pytest.mark.asyncio
async def test_stale_selection_stops_before_memory_and_vision_resolution():
    class Memory:
        async def get(self, visitor_id):
            raise AssertionError("stale selection must stop before memory access")

    async def resolve_vision(*args, **kwargs):
        raise AssertionError("stale selection must stop before vision resolution")

    resolver, _, rewriter, intent_router = _resolver(
        resolved=_resolved(warnings=("invalid_attraction_id",)),
        memory_repository=Memory(),
        vision_resolver=resolve_vision,
    )
    request = ChatRequest(
        query="路线规划",
        session_id="session-1",
        selection=SelectionContext(mode="attraction", attraction_id=5),
    )

    result = await resolver.resolve(request)

    assert result.error_code == "attraction_selection_stale"
    assert result.error_message == "所选景点已不可用或更新，请重新选择。"
    assert result.query_context is None
    assert rewriter.calls == []
    assert intent_router.calls == []


@pytest.mark.asyncio
async def test_memory_failure_is_fail_soft_and_vision_query_keeps_raw_intent():
    class FailingMemory:
        async def get(self, visitor_id):
            raise RuntimeError("memory unavailable")

    async def resolve_vision(vision, resolved, **kwargs):
        return SimpleNamespace(
            resolved=ResolvedInteraction(
                selection=resolved.selection,
                scope=None,
                resolution_source=resolved.resolution_source,
                active_subject=None,
                warnings=("vision_scope_unconfirmed",),
            ),
            confirmed_title=None,
            error_code=None,
            error_message=None,
        )

    resolver, _, rewriter, intent_router = _resolver(
        memory_repository=FailingMemory(), vision_resolver=resolve_vision
    )
    request = ChatRequest(
        query="这是什么？",
        session_id="session-2",
        visitor_id="visitor-1",
        audience="child",
        vision_context=VisionContext(
            candidate_attractions=["候选景点"], retrieval_query=" 候选视觉提示 "
        ),
        emotion_context=EmotionContext(
            audio_emotion="confused", audio_confidence=0.7, audio_source="test-audio"
        ),
    )

    result = await resolver.resolve(request)

    assert result.error_code is None
    assert result.audience == "child"
    assert result.memory_prompt is None
    assert result.resolved.active_subject is None
    assert result.confirmed_visual_title is None
    assert result.query_context.retrieval_query == "这是什么？\n候选视觉提示"
    assert result.query_context.normalized_query == "normalized:这是什么？\n候选视觉提示"
    assert rewriter.calls == [("这是什么？\n候选视觉提示", None)]
    assert intent_router.calls == [("这是什么？", result.resolved.selection)]
    assert result.audio_emotion.source == "test-audio"
    assert result.fused_emotion.label == EmotionLabel.CONFUSED
    assert result.response_policy == response_policy_for(result.fused_emotion)


@pytest.mark.asyncio
async def test_stale_vision_confirmation_returns_error_before_query_rewrite():
    async def resolve_vision(vision, resolved, **kwargs):
        return SimpleNamespace(
            resolved=resolved,
            confirmed_title=None,
            error_code="vision_confirmation_stale",
            error_message="景点已更新，请重新选择。",
        )

    resolver, _, rewriter, intent_router = _resolver(vision_resolver=resolve_vision)
    request = ChatRequest(
        query="介绍它",
        session_id="session-3",
        vision_context=VisionContext(candidate_attractions=["旧候选"]),
    )

    result = await resolver.resolve(request)

    assert result.error_code == "vision_confirmation_stale"
    assert result.query_context is None
    assert rewriter.calls == []
    assert intent_router.calls == []
