import asyncio
from pathlib import Path

from app.schemas.chat import ChatRequest
from app.schemas.live_data import LiveContext
from app.schemas.selection import SelectionContext
from app.services.avatar.stub import StubAvatarService
from app.services.coze.client import CozeRoutePlan
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.qa.cache import QACache
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.intent_router import IntentRouter
from app.services.qa.pipeline import QAPipeline
from app.services.rag.base import RetrievalScope, RetrievedDocument
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.stub import StubTTSService


class DummyCacheRepo:
    def __init__(self):
        self.set_keys = []

    def get(self, normalized_query):
        return None

    def set(self, normalized_query, answer, sources, expires_at):
        self.set_keys.append(normalized_query)
        return None

    def invalidate(self, normalized_query=None):
        return None


class DummyChatLogRepo:
    def create(self, **kwargs):
        return kwargs


class DummyRAGService:
    async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
        del query, normalized_query, top_k, scope
        return []


class DummyRouteRepository:
    class Route:
        id = "route_001"
        title = "亲子轻松线"
        duration_label = "2小时"
        route_plan = "入口 -> 灵山大佛 -> 梵宫"

    def list_all(self):
        return [self.Route()]


class DummyKnowledgeRepository:
    class Entry:
        def __init__(self, item_id, title, aliases=""):
            self.id = item_id
            self.title = title
            self.aliases = aliases

    def list_by_category(self, category):
        del category
        return [
            self.Entry(13, "灵山大佛", "大佛"),
            self.Entry(15, "梵宫", ""),
        ]


class RecordingBlindSpotTracker:
    def __init__(self):
        self.calls = []

    def record(self, **kwargs):
        self.calls.append(kwargs)


class DummyGuidedSelector:
    def resolve(self, query, selection, context):
        del query, context
        return ResolvedInteraction(
            selection=selection or SelectionContext(),
            scope=RetrievalScope(source_entry_id=13) if selection and selection.attraction_id else None,
            resolution_source="selection" if selection else "default",
            active_subject="灵山大佛" if selection and selection.attraction_id else None,
        )


class RecordingRAGService:
    def __init__(self):
        self.scopes = []

    async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
        del query, normalized_query, top_k
        self.scopes.append(scope)
        return [
            RetrievedDocument(
                title="官方景点",
                content="官方证据",
                snippet="官方证据",
                source="official.docx",
                score=1.0,
            )
        ]


class DummyLLMService:
    async def stream_generate(self, query, documents, *, persona=None):
        del query, documents, persona
        yield "基于官方证据回答。"


class FallbackLLMService:
    async def stream_generate(self, query, documents, *, persona=None):
        del query, documents, persona
        from app.services.llm.types import LLMStreamEvent

        yield LLMStreamEvent(type="content", text="证据降级回答。[证据1]")
        yield LLMStreamEvent(type="finish", finish_reason="fallback_http_429")


class DummyLiveDataService:
    def build_context(self, attractions):
        del attractions
        return LiveContext(
            is_mock=True,
            source_label="mock",
            weather={"condition": "晴"},
            visitor_flow={"level": "中等"},
            timestamp="2026-07-15T10:00:00+08:00",
        )


class DummyCozePlanner:
    is_configured = True

    async def run(self, payload):
        assert "route_candidates_json" in payload
        return CozeRoutePlan(
            answer="建议先去灵山大佛，再前往梵宫，当前天气和客流为演示模拟数据。",
            route_stops=[{"attraction_id": "13", "reason": "先看核心景点"}],
            adjustments=["客流中等，建议梵宫稍后进入"],
            sources=["官方路线候选", "实时上下文"],
            warning="",
            live_data_timestamp="2026-07-15T10:00:00+08:00",
            raw_payload={},
        )


async def collect_events():
    matcher = FAQMatcher()
    matcher.load_from_file(Path(__file__).resolve().parents[3] / "data" / "processed" / "faq_entries.json")
    from app.core.config import get_settings

    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=matcher,
        qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60),
        rag_service=DummyRAGService(),
        llm_service=OpenAICompatibleLLMService(get_settings()),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )

    events = []
    async for event in pipeline.stream_chat(
        ChatRequest(query="灵山大佛有多高", session_id="test-session", text_only=True),
    ):
        events.append(event.type)
    return events


def test_pipeline_faq_path_emits_done() -> None:
    events = asyncio.run(collect_events())

    assert "status" in events
    assert "context" in events
    assert "text" in events
    assert "followups" in events
    assert "done" in events


def test_pipeline_passes_resolved_scope_and_uses_selection_cache_key() -> None:
    cache_repository = DummyCacheRepo()
    rag_service = RecordingRAGService()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        rag_service=rag_service,
        llm_service=DummyLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )

    async def run():
        events = []
        async for event in pipeline.stream_chat(
            ChatRequest(
                query="有什么特色",
                session_id="selection-pipeline",
                text_only=True,
                selection=SelectionContext(mode="attraction", attraction_id=13),
            )
        ):
            events.append(event)
        return events

    events = asyncio.run(run())

    assert events[0].type == "context"
    assert events[0].data["selection"]["attraction_id"] == 13
    assert events[0].data["conversation_context"]["last_subject"] == "灵山大佛"
    assert rag_service.scopes == [RetrievalScope(source_entry_id=13)]
    source_event = next(event for event in events if event.type == "sources")
    assert source_event.data["docs"][0]["evidence_id"] == "证据1"
    assert len(cache_repository.set_keys) == 1
    assert cache_repository.set_keys[0].startswith("qa:v3:")
    assert events[-2].type == "followups"
    assert 2 <= len(events[-2].data["items"]) <= 4
    assert events[-1].type == "done"


def test_pipeline_records_blind_spot_only_when_rag_has_no_evidence() -> None:
    tracker = RecordingBlindSpotTracker()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60),
        rag_service=DummyRAGService(),
        llm_service=DummyLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
        blind_spot_tracker=tracker,
    )

    async def run():
        events = []
        async for event in pipeline.stream_chat(
            ChatRequest(query="卫生间在哪里", session_id="blind-spot", text_only=True)
        ):
            events.append(event)
        return events

    events = asyncio.run(run())

    assert tracker.calls == [
        {
            "raw_query": "卫生间在哪里",
            "normalized_query": "卫生间在哪里",
            "category": "rag_no_docs",
        }
    ]
    assert events[-1].type == "done"


def test_pipeline_does_not_cache_provider_fallback_answer() -> None:
    cache_repository = DummyCacheRepo()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        rag_service=RecordingRAGService(),
        llm_service=FallbackLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )

    async def run():
        return [
            event
            async for event in pipeline.stream_chat(
                ChatRequest(query="讲解景点", session_id="fallback-cache", text_only=True)
            )
        ]

    events = asyncio.run(run())

    assert cache_repository.set_keys == []
    assert events[-1].type == "done"


def test_direct_answer_appends_inline_citation_when_sources_exist() -> None:
    answer = QAPipeline._ensure_inline_citations(
        "灵山大佛高88米。",
        [{"evidence_id": "证据1", "title": "灵山大佛"}],
    )

    assert answer == "灵山大佛高88米。[证据1]"
    assert QAPipeline._ensure_inline_citations(answer, [{"evidence_id": "证据1"}]) == answer


def test_audio_event_contains_fallback_text_and_viseme_timeline() -> None:
    event = QAPipeline._build_audio_event(
        "灵山大佛。",
        "base64-audio",
        1200,
    )

    assert event.type == "audio"
    assert event.data["text"] == "灵山大佛。"
    assert event.data["base64"] == "base64-audio"
    assert event.data["duration_ms"] == 1200
    assert event.data["viseme_timeline"][0]["start"] == 0
    assert event.data["viseme_timeline"][-1]["end"] == 1200
    assert event.data["viseme_timeline"][-1]["value"] == 0.0


def test_pipeline_uses_dynamic_route_when_coze_is_available() -> None:
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60),
        rag_service=DummyRAGService(),
        llm_service=DummyLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
        intent_router=IntentRouter(),
        live_data_service=DummyLiveDataService(),
        coze_route_planner=DummyCozePlanner(),
        knowledge_repository=DummyKnowledgeRepository(),
        route_repository=DummyRouteRepository(),
    )

    async def run():
        return [
            event
            async for event in pipeline.stream_chat(
                ChatRequest(
                    query="请根据天气和客流推荐一条亲子路线",
                    session_id="dynamic-route",
                    text_only=True,
                    selection=SelectionContext(mode="route", route_id="route_001", available_hours=2),
                )
            )
        ]

    events = asyncio.run(run())

    intent_event = next(event for event in events if event.type == "intent")
    text_event = next(event for event in events if event.type == "text")
    assert intent_event.data["intent"] == "dynamic_route"
    assert "演示模拟数据" in text_event.data["text"]
    assert events[-1].type == "done"
