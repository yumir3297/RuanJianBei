import asyncio
from datetime import datetime, timezone

from app.models.guide_loop import GuideLoopCase, GuideLoopCheck, GuideLoopPointer, GuideLoopRevision
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.schemas.chat import ChatRequest
from app.schemas.selection import SelectionContext
from app.services.guide_loop.publication import resolve_visitor_answer
from app.tests.async_db import open_test_session
from app.tests.test_pipeline import _build_test_pipeline


def test_visitor_answer_requires_bound_current_reviewed_and_confirmed_revision(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "visitor.db"))
        try:
            entry = KnowledgeEntry(id=13, title="演示景点", category="景点信息", content="合成资料", source="合成来源")
            case = GuideLoopCase(cluster_id="demo", category="retrieval_gap", status="closed")
            session.add_all([entry, case])
            await session.flush()
            revision = KnowledgeRevision(id="k01-v1", knowledge_entry_id=13, title="演示景点", category="景点信息", content="合成资料", source="合成来源")
            session.add(revision)
            await session.flush()
            entry.published_revision_id = revision.id
            now = datetime.now(timezone.utc)
            session.add_all([
                GuideLoopPointer(scope_key="demo:target", poi_id="demo", target_id="target", revision_id="gl-v1"),
                GuideLoopRevision(revision_id="gl-v1", base_revision="0", case_id="demo", poi_id="demo", target_id="target", action="add_alias", alias="演示问题", answer="合成已审核回答", evidence_id="synthetic", source_ref="合成来源", knowledge_entry_id=13, knowledge_revision_id="k01-v1", effective_from=now.replace(year=2020), status="published", source_reviewed=True, created_at=now),
                GuideLoopCheck(check_id="check", case_id="demo", revision_id="gl-v1", decision="answer", passed=True, operator_passed=True),
            ])
            await session.commit()
            pipeline = _build_test_pipeline(guide_loop_session=session, guide_loop_visitor_enabled=True)
            events = [event async for event in pipeline.stream_chat(ChatRequest(query="演示问题", session_id="visitor", text_only=True, selection=SelectionContext(attraction_id=13)))]
            assert any(event.type == "text" and "合成已审核回答" in event.data["text"] for event in events)
            class Gate:
                def __init__(self, result):
                    self.result = result
                def decide(self, query, candidate):
                    assert (query, candidate) == ("演示问题呀", "演示问题")
                    return self.result
            assert (await resolve_visitor_answer(session, entry_id=13, query="演示问题呀", guidematch_gate=Gate("reuse")))["decision"] == "answer"
            assert (await resolve_visitor_answer(session, entry_id=13, query="演示问题呀", guidematch_gate=Gate("distinct")))["decision"] == "pass"
            assert (await resolve_visitor_answer(session, entry_id=13, query="演示问题呀"))["decision"] == "pass"
            assert (await resolve_visitor_answer(session, entry_id=999, query="演示问题"))["decision"] == "pass"
            case.status = "published_pending_check"
            await session.commit()
            assert (await resolve_visitor_answer(session, entry_id=13, query="演示问题"))["decision"] == "unavailable"
            case.status = "closed"
            entry.withdrawn_at = now
            await session.commit()
            withheld = await resolve_visitor_answer(session, entry_id=13, query="演示问题")
            assert withheld["decision"] == "unavailable" and "合成已审核回答" not in str(withheld)
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())
