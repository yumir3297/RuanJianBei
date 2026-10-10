import asyncio
from types import SimpleNamespace
from pathlib import Path

from app.schemas.chat import ChatRequest
from app.schemas.selection import SelectionContext
from app.services.avatar.stub import StubAvatarService
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.qa.cache import QACache
from app.services.qa.faq_matcher import FAQEntry, FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.intent_router import IntentRouter
from app.services.qa.pipeline import QAPipeline
from app.services.rag.base import RetrievalScope, RetrievedDocument
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.stub import StubTTSService
from app.services.tts.streaming import StreamingTTSEvent


class DummyCacheRepo:
    def __init__(self):
        self.set_keys = []

    async def get(self, normalized_query):
        return None

    async def set(self, normalized_query, answer, sources, expires_at):
        self.set_keys.append(normalized_query)
        return None

    async def invalidate(self, normalized_query=None):
        return None


class DummyChatLogRepo:
    async def create(self, **kwargs):
        return SimpleNamespace(id=1, **kwargs)


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
        guide_points_json = "[]"
        experiences_json = "[]"
        source = "官方路线模板"
        tags = "亲子|家庭|互动"

    async def list_all(self):
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

    async def record(self, **kwargs):
        self.calls.append(kwargs)


class DummyGuidedSelector:
    async def resolve(self, query, selection, context):
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
    def __init__(self):
        self.received = []

    async def stream_generate(self, query, documents, *, persona=None, audience=None, memory=None):
        self.received.append(
            {
                "query": query,
                "documents": list(documents),
                "persona": persona,
                "audience": audience,
                "memory": memory,
            }
        )
        yield "基于官方证据回答。"


class FakeStreamingTTSSession:
    def __init__(self):
        self.events = asyncio.Queue()
        self.sent_text = []
        self.closed = False

    async def connect(self):
        return None

    async def send_text(self, text):
        self.sent_text.append(text)
        await self.events.put(StreamingTTSEvent(type="audio_chunk", data=b"\x00\x00" * 20))
        await self.events.put(StreamingTTSEvent(type="word_timestamps", data={
            "words": [{"text": "答", "begin_time": 0, "end_time": 100}],
            "characters": sum(len(item) for item in self.sent_text),
            "sentence_index": 0,
        }))

    async def finish(self):
        await self.events.put(StreamingTTSEvent(type="done"))

    async def receive(self, timeout=None):
        del timeout
        return await self.events.get()

    async def close(self):
        self.closed = True


class FakeStreamingTTSService:
    def __init__(self):
        self.session = FakeStreamingTTSSession()

    def create_session(self):
        return self.session


class FallbackLLMService:
    async def stream_generate(self, query, documents, *, persona=None, audience=None, memory=None):
        del query, documents, persona, audience, memory
        from app.services.llm.types import LLMStreamEvent

        yield LLMStreamEvent(type="content", text="证据降级回答。[证据1]")
        yield LLMStreamEvent(type="finish", finish_reason="fallback_http_429")


class DummyVisitorMemoryRepo:
    """替身仓储：只替换 I/O，不替换记忆解码与提示词构建（那是真实代码）。"""

    def __init__(self, memory=None):
        self.memory = memory
        self.recorded = []

    async def get(self, visitor_id, *, site_id="default"):
        return self.memory

    async def record_visit(self, **kwargs):
        self.recorded.append(kwargs)
        return self.memory


def _memory_row(**overrides):
    from app.models.visitor_memory import VisitorMemory

    values = {
        "visitor_id": "v-1",
        "site_id": "default",
        "visited_attractions": '["灵山大佛"]',
        "preference_tags": "[]",
        "narration_audience": "child",
        "visit_count": 2,
        "last_session_id": "s-0",
    }
    values.update(overrides)
    return VisitorMemory(**values)


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
    llm_service = DummyLLMService()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        rag_service=rag_service,
        llm_service=llm_service,
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
    assert cache_repository.set_keys[0].startswith("qa:v4:")
    assert events[-2].type == "followups"
    assert 2 <= len(events[-2].data["items"]) <= 4
    assert events[-1].type == "done"
    # 受众必须一路透传到 LLM（未指定 == adult）
    assert llm_service.received[-1]["audience"] == "adult"


def test_pipeline_forwards_child_audience_to_llm_and_cache_key() -> None:
    cache_repository = DummyCacheRepo()
    llm_service = DummyLLMService()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        rag_service=RecordingRAGService(),
        llm_service=llm_service,
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )

    def run(audience):
        async def scenario():
            events = []
            async for event in pipeline.stream_chat(
                ChatRequest(
                    query="有什么特色",
                    session_id=f"audience-{audience}",
                    text_only=True,
                    selection=SelectionContext(mode="attraction", attraction_id=13),
                    audience=audience,
                )
            ):
                events.append(event)
            return events

        return asyncio.run(scenario())

    cache_repository.set_keys.clear()
    run("child")
    assert llm_service.received[-1]["audience"] == "child"
    child_keys = set(cache_repository.set_keys)

    cache_repository.set_keys.clear()
    run("expert")
    assert llm_service.received[-1]["audience"] == "expert"
    expert_keys = set(cache_repository.set_keys)

    assert child_keys and expert_keys
    assert child_keys.isdisjoint(expert_keys), "不同受众不得共用缓存键"


def _build_test_pipeline(**overrides):
    kwargs = dict(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60),
        rag_service=RecordingRAGService(),
        llm_service=DummyLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )
    kwargs.update(overrides)
    return QAPipeline(**kwargs)


def _run_turn(pipeline, **request_overrides):
    request_kwargs = {
        "query": "有什么特色",
        "session_id": "s-1",
        "text_only": True,
        "selection": SelectionContext(mode="attraction", attraction_id=13),
    }
    request_kwargs.update(request_overrides)

    async def scenario():
        events = []
        async for event in pipeline.stream_chat(ChatRequest(**request_kwargs)):
            events.append(event)
        return events

    return asyncio.run(scenario())


def test_pipeline_injects_visitor_memory_and_records_visit() -> None:
    llm_service = DummyLLMService()
    memory_repo = DummyVisitorMemoryRepo(_memory_row())
    pipeline = _build_test_pipeline(
        llm_service=llm_service,
        visitor_memory_repository=memory_repo,
    )

    _run_turn(pipeline, visitor_id="v-1")

    memory_prompt = llm_service.received[-1]["memory"]
    assert memory_prompt is not None
    assert "【游客记忆】" in memory_prompt
    assert "欢迎回来" in memory_prompt
    assert "灵山大佛" in memory_prompt

    recorded = memory_repo.recorded[-1]
    assert recorded["visitor_id"] == "v-1"
    assert recorded["session_id"] == "s-1"
    assert recorded["attraction_title"] == "灵山大佛"
    assert recorded["narration_audience"] == "adult"


def test_pipeline_without_visitor_id_never_touches_memory() -> None:
    llm_service = DummyLLMService()
    memory_repo = DummyVisitorMemoryRepo(_memory_row())
    pipeline = _build_test_pipeline(
        llm_service=llm_service,
        visitor_memory_repository=memory_repo,
    )

    _run_turn(pipeline)

    assert llm_service.received[-1]["memory"] is None
    assert memory_repo.recorded == []


def test_pipeline_forwards_streaming_tts_events_without_waiting_for_http_audio() -> None:
    streaming_tts = FakeStreamingTTSService()
    pipeline = QAPipeline(
        query_rewriter=QueryRewriter(),
        faq_matcher=FAQMatcher(),
        qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60),
        rag_service=RecordingRAGService(),
        llm_service=DummyLLMService(),
        tts_service=StubTTSService(),
        avatar_service=StubAvatarService(),
        streaming_tts_service=streaming_tts,
        chat_log_repository=DummyChatLogRepo(),
        guided_selector=DummyGuidedSelector(),
        followup_suggestions=FollowUpSuggestionService(),
    )

    async def run():
        return [
            event
            async for event in pipeline.stream_chat(
                ChatRequest(query="介绍灵山大佛", session_id="streaming-tts")
            )
        ]

    events = asyncio.run(run())
    event_types = [event.type for event in events]

    assert event_types.count("audio_chunk") == 2
    assert "audio" not in event_types
    assert streaming_tts.session.sent_text == ["基于官方证据回答。"]
    assert streaming_tts.session.closed is True
    assert event_types[-1] == "done"


def test_streaming_word_timestamps_event_converts_to_real_viseme_timeline() -> None:
    """词级时间戳必须原样驱动口型时间线，而不是退回 pypinyin 均匀估算。"""
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
    )

    event = StreamingTTSEvent(type="word_timestamps", data={
        "words": [
            {"text": "灵山", "begin_time": 0, "end_time": 200},
            {"text": "大佛", "begin_time": 200, "end_time": 500},
        ],
        "sentence_index": 2,
        "characters": 4,
    })

    sse_events = pipeline._handle_streaming_tts_event(event)

    assert len(sse_events) == 1
    assert sse_events[0].type == "audio_chunk"
    assert sse_events[0].data["sentence_index"] == 2
    timeline = sse_events[0].data["viseme_timeline"]
    # CosyVoice 字级时间戳：每个字一个词条，每词条一帧
    assert len(timeline) == 2
    assert timeline[0]["start"] == 0
    assert timeline[0]["end"] == 200   # 帧边界严格来自真实时间戳
    assert timeline[1]["start"] == 200
    assert timeline[-1]["end"] == 500  # 结束时间来自真实时间戳而非估算
    for frame in timeline:
        assert set(frame) == {"start", "end", "value", "form"}


def test_streaming_word_timestamps_event_carries_raw_word_timeline() -> None:
    """word_timestamps 必须同时下发原始逐字时间（word_timeline），供前端字幕逐字同步。"""
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
    )

    event = StreamingTTSEvent(type="word_timestamps", data={
        "words": [
            {"text": "灵山", "begin_time": 0, "end_time": 200},
            {"text": "大佛", "begin_time": 200, "end_time": 500},
        ],
        "sentence_index": 2,
        "characters": 4,
    })

    sse_events = pipeline._handle_streaming_tts_event(event)

    chunk = next(e for e in sse_events if e.type == "audio_chunk")
    # 原始逐字时间必须原样透传（text/begin_time/end_time），不得只转口型
    assert chunk.data["word_timeline"] == [
        {"text": "灵山", "begin_time": 0, "end_time": 200},
        {"text": "大佛", "begin_time": 200, "end_time": 500},
    ]


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


def test_pipeline_uses_backend_preset_route() -> None:
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
        knowledge_repository=DummyKnowledgeRepository(),
        route_repository=DummyRouteRepository(),
    )

    async def run():
        return [
            event
            async for event in pipeline.stream_chat(
                ChatRequest(
                    query="请根据天气和客流推荐一条亲子路线",
                    session_id="preset-route",
                    text_only=True,
                    selection=SelectionContext(mode="route", route_id="route_001", available_hours=2),
                )
            )
        ]

    events = asyncio.run(run())

    intent_event = next(event for event in events if event.type == "intent")
    text_event = next(event for event in events if event.type == "text")
    assert intent_event.data["intent"] == "static_route"
    assert "亲子轻松线" in text_event.data["text"]
    assert events[-1].type == "done"


def _faq_matcher():
    matcher = FAQMatcher()
    matcher.add(
        [
            FAQEntry(
                id="faq-opening",
                category="practical",
                aliases=["几点开门"],
                answer="灵山胜境每日 8:00 开门，17:00 停止入园。",
                sources=["景区官方公告"],
            )
        ]
    )
    return matcher


def test_faq_fast_path_stays_llm_free_for_default_audience() -> None:
    llm_service = DummyLLMService()
    rag_service = RecordingRAGService()
    pipeline = _build_test_pipeline(
        faq_matcher=_faq_matcher(),
        llm_service=llm_service,
        rag_service=rag_service,
    )

    events = _run_turn(pipeline, query="几点开门")

    assert llm_service.received == [], "默认受众下 FAQ 快路径不应调用 LLM"
    assert rag_service.scopes == [], "FAQ 命中不应触发 RAG 检索"
    text_event = next(event for event in events if event.type == "text")
    assert "8:00" in text_event.data["text"]
    assert events[-1].data["hit_level"] == "faq_exact"


def test_faq_path_restyles_through_llm_for_child_audience() -> None:
    llm_service = DummyLLMService()
    rag_service = RecordingRAGService()
    pipeline = _build_test_pipeline(
        faq_matcher=_faq_matcher(),
        llm_service=llm_service,
        rag_service=rag_service,
    )

    events = _run_turn(pipeline, query="几点开门", audience="child")

    assert len(llm_service.received) == 1, "非默认受众下 FAQ 必须走 LLM 改写"
    assert llm_service.received[-1]["audience"] == "child"
    assert rag_service.scopes == [], "FAQ 命中仍不应触发 RAG 检索"

    documents = llm_service.received[-1]["documents"]
    assert len(documents) == 1, "FAQ 原文应作为唯一证据交给 LLM"
    assert "8:00" in documents[0].content

    assert events[-1].data["hit_level"] == "faq_exact_styled"


def test_faq_path_keeps_adult_on_fast_path_when_audience_is_adult() -> None:
    llm_service = DummyLLMService()
    pipeline = _build_test_pipeline(faq_matcher=_faq_matcher(), llm_service=llm_service)

    events = _run_turn(pipeline, query="几点开门", audience="adult")

    assert llm_service.received == [], "adult 与未指定等价，不应触发 LLM"
    assert events[-1].data["hit_level"] == "faq_exact"


def test_faq_styled_answer_is_cached_under_audience_specific_key() -> None:
    cache_repository = DummyCacheRepo()
    pipeline = _build_test_pipeline(
        faq_matcher=_faq_matcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        llm_service=DummyLLMService(),
    )

    _run_turn(pipeline, query="几点开门", audience="child")

    assert len(cache_repository.set_keys) == 1
    assert cache_repository.set_keys[0].startswith("qa:v4:")


def test_faq_answer_survives_llm_outage_for_non_default_audience() -> None:
    """LLM 降级时不能把"服务暂不可用"甩给游客——FAQ 原文本身权威且完整，应回落原文。"""
    cache_repository = DummyCacheRepo()
    pipeline = _build_test_pipeline(
        faq_matcher=_faq_matcher(),
        qa_cache=QACache(cache_repository, ttl_seconds=60),
        llm_service=FallbackLLMService(),
    )

    events = _run_turn(pipeline, query="几点开门", audience="child")

    text_event = next(event for event in events if event.type == "text")
    assert "8:00" in text_event.data["text"], "应回落 FAQ 原文"
    assert "证据降级回答" not in text_event.data["text"]

    assert events[-1].data["degraded"] is True
    assert events[-1].data["hit_level"] == "faq_exact_styled_llm_fallback"
    assert cache_repository.set_keys == [], "未按受众改写的答案不得写入受众专属缓存"
