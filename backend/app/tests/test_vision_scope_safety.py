import asyncio
import pytest
from types import SimpleNamespace
from app.schemas.chat import ChatRequest, VisionContext, ConversationContext
from app.schemas.selection import SelectionContext
from app.services.qa.pipeline import QAPipeline
from app.services.qa.cache import QACache
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.stub import StubTTSService
from app.services.avatar.stub import StubAvatarService
from app.tests.test_pipeline import DummyCacheRepo, DummyChatLogRepo, DummyGuidedSelector, DummyLLMService, RecordingRAGService

@pytest.mark.parametrize('candidates,confidence', [(['梵宫'], 0), (['梵宫','灵山大佛'], 1)])
@pytest.mark.parametrize('selected', [False, True])
def test_visual_clues_do_not_silently_scope_or_cache(candidates, confidence, selected):
    class Selector(DummyGuidedSelector):
        async def find_attraction_by_candidates(self, names):
            return SimpleNamespace(id=15, title='梵宫')
    class CacheRepo(DummyCacheRepo):
        def __init__(self):
            super().__init__(); self.reads = 0
        async def get(self, key):
            self.reads += 1
            return None
    cache = CacheRepo(); rag = RecordingRAGService()
    pipeline = QAPipeline(query_rewriter=QueryRewriter(), faq_matcher=FAQMatcher(), qa_cache=QACache(cache, ttl_seconds=60), rag_service=rag, llm_service=DummyLLMService(), tts_service=StubTTSService(), avatar_service=StubAvatarService(), chat_log_repository=DummyChatLogRepo(), guided_selector=Selector(), followup_suggestions=FollowUpSuggestionService())
    request = ChatRequest(query='请介绍照片', session_id='v', text_only=True, vision_context=VisionContext(candidate_attractions=candidates, confidence=confidence), selection=SelectionContext(mode='attraction', attraction_id=13) if selected else None, context=ConversationContext(last_subject='灵山大佛'))
    async def run(): return [e async for e in pipeline.stream_chat(request)]
    events=asyncio.run(run())
    context=next(e.data for e in events if e.type=='context')
    assert 'vision_scope_unconfirmed' in context['warnings']
    if selected:
        assert context['selection']['attraction_id'] == 13
    assert rag.scopes and rag.scopes[0] is None
    assert cache.reads == 0 and cache.set_keys == []


def test_vision_without_evidence_refuses_without_calling_model():
    class EmptyRag:
        async def retrieve(self, *args, **kwargs): return []
    class MustNotCall:
        async def stream_generate(self, *args, **kwargs):
            raise AssertionError("model must not be called without evidence")
            yield
    cache = DummyCacheRepo()
    pipeline = QAPipeline(query_rewriter=QueryRewriter(), faq_matcher=FAQMatcher(), qa_cache=QACache(cache, ttl_seconds=60), rag_service=EmptyRag(), llm_service=MustNotCall(), tts_service=StubTTSService(), avatar_service=StubAvatarService(), chat_log_repository=DummyChatLogRepo(), guided_selector=DummyGuidedSelector(), followup_suggestions=FollowUpSuggestionService())
    async def run():
        return [e async for e in pipeline.stream_chat(ChatRequest(query="介绍照片", session_id="v-empty", text_only=True, vision_context=VisionContext(candidate_attractions=["未知景点"])))]
    events = asyncio.run(run())
    assert any(e.type == "done" and e.data.get("hit_level") == "rag_insufficient" for e in events)
    assert not any(e.type == "sources" and e.data.get("docs") for e in events)


def test_vision_retrieval_query_is_used_as_untrusted_search_hint():
    class Rag(RecordingRAGService):
        async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
            self.query = query
            return await super().retrieve(query, normalized_query, top_k, scope)
    rag = Rag()
    llm = DummyLLMService()
    pipeline = QAPipeline(query_rewriter=QueryRewriter(), faq_matcher=FAQMatcher(), qa_cache=QACache(DummyCacheRepo(), ttl_seconds=60), rag_service=rag, llm_service=llm, tts_service=StubTTSService(), avatar_service=StubAvatarService(), chat_log_repository=DummyChatLogRepo(), guided_selector=DummyGuidedSelector(), followup_suggestions=FollowUpSuggestionService())
    async def run():
        return [e async for e in pipeline.stream_chat(ChatRequest(query="介绍照片", session_id="v-hint", text_only=True, vision_context=VisionContext(retrieval_query="梵宫莲花穹顶")))]
    asyncio.run(run())
    assert "梵宫莲花穹顶" in rag.query
    assert "未经确认" in llm.received[0]["query"]
    assert "不要断言照片" in llm.received[0]["query"]
