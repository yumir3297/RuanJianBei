import asyncio
from datetime import datetime, timedelta, timezone
from app.models.guide_loop import GuideLoopCase, GuideLoopCheck, GuideLoopPointer, GuideLoopRevision
from app.schemas.chat import ChatRequest
from app.schemas.guide_loop import GuideLoopContext
from app.services.qa.faq_matcher import FAQEntry, FAQMatcher
from app.repositories.guide_loop import GuideLoopRepository
from app.services.guide_loop.publication import resolve_public_answer
from app.tests.async_db import open_test_session
from app.tests.test_pipeline import _build_test_pipeline


def test_published_alias_answers_before_generic_pipeline_and_emits_check_context(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "chat.db"))
        try:
            now=datetime.now(timezone.utc)
            session.add(GuideLoopCase(cluster_id="case",category="retrieval_gap",status="published_pending_check"))
            session.add(GuideLoopPointer(scope_key="bathing:prince",poi_id="bathing",target_id="prince",revision_id="gl-v1"))
            session.add(GuideLoopRevision(revision_id="gl-v1",base_revision="0",case_id="case",poi_id="bathing",target_id="prince",action="add_alias",alias="莲花里是谁",answer="莲花里有太子佛立像。",evidence_id="gazetteer-1",source_ref="公开方志",effective_from=now.replace(year=2020),effective_until=None,status="published",source_reviewed=True,created_at=now))
            await session.commit()
            pipeline=_build_test_pipeline(guide_loop_session=session)
            events=[event async for event in pipeline.stream_chat(ChatRequest(query="莲花里是谁？",session_id="fresh",text_only=True,guide_loop=GuideLoopContext(poi_id="bathing")))]
            context=next(event for event in events if event.type=="context")
            answer=next(event for event in events if event.type=="text").data["text"]
            assert context.data["guide_loop"]["decision"]=="answer"
            assert context.data["guide_loop"]["revision_id"]=="gl-v1"
            assert context.data["guide_loop"]["check_id"]
            assert "太子佛立像" in answer
            assert not pipeline.rag_service.scopes
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_withdrawn_alias_never_falls_through_to_old_answer(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "withdraw.db"))
        try:
            now=datetime.now(timezone.utc)
            session.add(GuideLoopCase(cluster_id="case",category="stale_or_conflict",status="published_pending_check"))
            session.add(GuideLoopPointer(scope_key="bathing:show",poi_id="bathing",target_id="show",revision_id="gl-v2"))
            session.add(GuideLoopRevision(revision_id="gl-v2",base_revision="gl-v1",case_id="case",poi_id="bathing",target_id="show",action="withdraw",alias="今天下一场几点",answer=None,evidence_id="notice-1",source_ref="模拟公告",effective_from=now.replace(year=2020),effective_until=None,status="withdrawn",created_at=now))
            await session.commit()
            stale_faq = FAQMatcher()
            stale_faq.add([FAQEntry(id="old-show-time", category="practical", aliases=["今天下一场几点"], answer="旧答案：下一场 14:00。", sources=["旧公告"])])
            pipeline=_build_test_pipeline(faq_matcher=stale_faq, guide_loop_session=session)
            events=[event async for event in pipeline.stream_chat(ChatRequest(query="今天下一场几点？",session_id="fresh",text_only=True,guide_loop=GuideLoopContext(poi_id="bathing")))]
            answer=next(event for event in events if event.type=="text").data["text"]
            assert "无法核实" in answer
            assert "14:00" not in answer
            context = next(event.data["guide_loop"] for event in events if event.type == "context")
            assert context["decision"] == "unavailable"
            assert not pipeline.rag_service.scopes
            check = await session.get(GuideLoopCheck, next(event.data["guide_loop"]["check_id"] for event in events if event.type == "context"))
            assert check.passed is True
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_revision_validity_uses_inclusive_start_and_exclusive_end(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "revision-validity.db"))
        try:
            start = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
            end = datetime(2026, 11, 10, 13, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="timed", category="stale_or_conflict", status="published_pending_check"),
                GuideLoopPointer(scope_key="bathing:show", poi_id="bathing", target_id="show", revision_id="gl-timed"),
                GuideLoopRevision(revision_id="gl-timed", base_revision="gl-old", case_id="timed", poi_id="bathing", target_id="show", action="add_alias", alias="最近一场几点", answer="模拟场次为十二点半开始。", evidence_id="notice-1", source_ref="合成测试公告", effective_from=start, effective_until=end, status="published", source_reviewed=True, created_at=start),
            ])
            await session.commit()
            before = await resolve_public_answer(session, poi_id="bathing", query="最近一场几点？", now=start - timedelta(seconds=1))
            at_start = await resolve_public_answer(session, poi_id="bathing", query="最近一场几点？", now=start)
            at_end = await resolve_public_answer(session, poi_id="bathing", query="最近一场几点？", now=end)
            assert before["decision"] == "unavailable"
            assert "十二点半" not in before["answer"]
            assert at_start["decision"] == "answer"
            assert "十二点半" in at_start["answer"]
            assert at_end["decision"] == "unavailable"
            assert "十二点半" not in at_end["answer"]
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_legacy_revision_without_source_review_is_withheld(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "legacy-unreviewed.db"))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="legacy", category="retrieval_gap", status="published_pending_check"),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-legacy"),
                GuideLoopRevision(revision_id="gl-legacy", base_revision="0", case_id="legacy", poi_id="bathing", target_id="prince", action="add_alias", alias="莲花里是谁", answer="历史旧答案。", evidence_id="e-old", source_ref="历史来源", effective_from=now.replace(year=2020), status="published", source_reviewed=False, created_at=now),
            ])
            await session.commit()
            result = await resolve_public_answer(session, poi_id="bathing", query="莲花里是谁？", now=now)
            assert result["decision"] == "unavailable"
            assert "历史旧答案" not in result["answer"]
            assert result["sources"][0]["title"] == "待来源复核记录"
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_admin_replay_persists_check_and_can_be_confirmed(tmp_path, monkeypatch):
    import json
    from app.api import chat
    from app.repositories.chat_log import ChatLogRepository
    from app.tests.test_guide_loop_matching import build_client

    db_path = tmp_path / 'admin-replay.db'
    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            now = datetime.now(timezone.utc)
            session.add(GuideLoopCase(cluster_id='case', category='retrieval_gap', status='published_pending_check', draft_hash='gl-v1'))
            session.add(GuideLoopPointer(scope_key='bathing:prince', poi_id='bathing', target_id='prince', revision_id='gl-v1'))
            session.add(GuideLoopRevision(revision_id='gl-v1', base_revision='0', case_id='case', poi_id='bathing', target_id='prince', action='add_alias', alias='莲花里是谁', answer='莲花里有太子佛立像。', evidence_id='gazetteer-1', source_ref='公开方志', effective_from=now.replace(year=2020), status='published', source_reviewed=True, created_at=now))
            await session.commit()
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(seed())

    async def stub_pipeline(session, settings, **_kwargs):
        return _build_test_pipeline(guide_loop_session=session, chat_log_repository=ChatLogRepository(session))
    monkeypatch.setattr(chat, 'build_pipeline', stub_pipeline)
    with build_client(db_path, admin=True) as client:
        from app.core.deps import get_db_session
        async def checked_session():
            engine, session = await open_test_session(str(db_path))
            try:
                yield session
            finally:
                await session.close()
                assert engine.pool.checkedout() == 0
                await engine.dispose()
        client.app.dependency_overrides[get_db_session] = checked_session
        response = client.post('/api/admin/guide-loop/replay', json={'query': '莲花里是谁？', 'session_id': 'new-visitor', 'text_only': True, 'guide_loop': {'poi_id': 'bathing'}})
        assert response.status_code == 200
        blocks = response.text.replace('\r\n', '\n').split('\n\n')
        context_block = next(block for block in blocks if block.startswith('event: context\n'))
        context = json.loads(next(line[6:] for line in context_block.splitlines() if line.startswith('data: ')))
        assert context['guide_loop']['decision'] == 'answer'
        assert 'event: done' in response.text, response.text
        assert 'event: error' not in response.text, response.text
        check_id = context['guide_loop']['check_id']
        assert '太子佛立像' in response.text
        confirmed = client.post('/api/admin/guide-loop/confirm-live', json={'check_id': check_id, 'passed': True})
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()['status'] == 'closed'
