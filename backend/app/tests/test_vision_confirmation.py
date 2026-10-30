import asyncio
import pytest
from app.schemas.chat import ChatRequest, VisionContext
from app.services.itinerary.catalog import PublishedAttraction, CatalogSnapshot
from app.services.qa.pipeline import QAPipeline
from app.services.qa.cache import QACache
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.tts.stub import StubTTSService
from app.services.avatar.stub import StubAvatarService
from app.tests.test_pipeline import DummyCacheRepo, DummyChatLogRepo, DummyGuidedSelector, DummyLLMService, RecordingRAGService

@pytest.mark.parametrize('site,code,rev,valid', [('park','a','rev1',True),('other','a','rev1',False),('park','missing','rev1',False),('park','a','old',False)])
def test_confirmed_visual_spot_requires_active_catalog(site,code,rev,valid):
    class Catalog:
        async def list_for_site(self, site):
            assert site == 'park'
            return CatalogSnapshot('park',(PublishedAttraction('park','a','13','rev1','景点'),),'d')
    rag=RecordingRAGService()
    pipeline=QAPipeline(query_rewriter=QueryRewriter(),faq_matcher=FAQMatcher(),qa_cache=QACache(DummyCacheRepo(),ttl_seconds=60),rag_service=rag,llm_service=DummyLLMService(),tts_service=StubTTSService(),avatar_service=StubAvatarService(),chat_log_repository=DummyChatLogRepo(),guided_selector=DummyGuidedSelector(),followup_suggestions=FollowUpSuggestionService(),vision_catalog=Catalog(),vision_site_id='park')
    vision=VisionContext(candidate_attractions=['景点'],confirmation={'site_id':site,'spot_code':code,'published_revision_id':rev})
    async def run():return [e async for e in pipeline.stream_chat(ChatRequest(query='介绍照片',session_id='v',text_only=True,vision_context=vision))]
    events=asyncio.run(run())
    if valid:
        assert rag.scopes[0].source_entry_id == 13
        assert not any(e.type=='error' for e in events)
    else:
        assert not rag.scopes
        assert any(e.type=='error' for e in events)

def test_confirmed_spot_withdrawn_after_selection_is_rejected_with_real_catalog():
    from datetime import UTC, datetime
    from app.models.knowledge import KnowledgeEntry
    from app.models.knowledge_workspace import KnowledgeRevision
    from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
    from app.tests.async_db import open_test_session
    import json
    async def run():
        engine, db = await open_test_session()
        try:
            entry = KnowledgeEntry(title='景点',category='景点信息',content='介绍',source='资料',aliases='',metadata_json=json.dumps({'attraction_id':'a'}))
            db.add(entry); await db.flush()
            revision=KnowledgeRevision(id='rev1',knowledge_entry_id=entry.id,title=entry.title,category=entry.category,content=entry.content,source=entry.source,aliases='',metadata_json=entry.metadata_json)
            db.add(revision); await db.flush(); entry.published_revision_id='rev1'; await db.commit()
            catalog=PublishedAttractionCatalog(K01PublishedAttractionSource(db,site_id='park'))
            rag=RecordingRAGService()
            pipeline=QAPipeline(query_rewriter=QueryRewriter(),faq_matcher=FAQMatcher(),qa_cache=QACache(DummyCacheRepo(),ttl_seconds=60),rag_service=rag,llm_service=DummyLLMService(),tts_service=StubTTSService(),avatar_service=StubAvatarService(),chat_log_repository=DummyChatLogRepo(),guided_selector=DummyGuidedSelector(),followup_suggestions=FollowUpSuggestionService(),vision_catalog=catalog,vision_site_id='park')
            req=ChatRequest(query='介绍照片',session_id='v',text_only=True,vision_context=VisionContext(confirmation={'site_id':'park','spot_code':'a','published_revision_id':'rev1'}))
            before=[e async for e in pipeline.stream_chat(req)]
            assert rag.scopes[-1].source_entry_id == entry.id
            entry.withdrawn_at=datetime.now(UTC); await db.commit(); rag.scopes.clear()
            after=[e async for e in pipeline.stream_chat(req)]
            assert any(e.type=='error' for e in after) and not rag.scopes
        finally:
            await db.close(); await engine.dispose()
    asyncio.run(run())
