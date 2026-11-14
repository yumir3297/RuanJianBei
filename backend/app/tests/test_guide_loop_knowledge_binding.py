import asyncio
from datetime import datetime, timezone

import pytest

from app.models.guide_loop import GuideLoopCase
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.schemas.guide_loop import DraftRequest
from app.services.guide_loop.publication import GuideLoopPublicationService, resolve_public_answer
from app.tests.async_db import open_test_session


def test_bound_answer_is_withheld_after_republication_or_withdrawal(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "binding.db"))
        try:
            entry = KnowledgeEntry(title="条目", category="general", content="内容", source="来源")
            session.add_all([entry, GuideLoopCase(cluster_id="bound", category="retrieval_gap", status="open")])
            await session.flush()
            revision = KnowledgeRevision(id="revision-one", knowledge_entry_id=entry.id, title="条目", category="general", content="内容", source="来源")
            session.add(revision)
            await session.flush()
            entry.published_revision_id = revision.id
            await session.commit()
            payload = DraftRequest(base_revision="0", action="add_alias", poi_id="park", target_id="object", alias="测试问题", answer="旧回答", evidence={"evidence_id": "e1", "source_ref": "来源"}, knowledge_entry_id=entry.id, knowledge_revision_id=revision.id, effective_from="2020-01-01T00:00:00Z")
            service = GuideLoopPublicationService(session)
            case = await service.create_draft("bound", payload)
            await session.commit()
            await service.verify("bound", case.draft_id)
            await session.commit()
            published = await service.publish("bound", case.draft_id, "0", source_reviewed=True)
            await session.commit()
            assert (published.knowledge_entry_id, published.knowledge_revision_id) == (entry.id, revision.id)
            assert (await resolve_public_answer(session, poi_id="park", query="测试问题"))["answer"] == "旧回答"

            newer = KnowledgeRevision(id="revision-two", knowledge_entry_id=entry.id, title="条目", category="general", content="新内容", source="来源")
            session.add(newer)
            await session.flush()
            entry.published_revision_id = newer.id
            await session.commit()
            result = await resolve_public_answer(session, poi_id="park", query="测试问题")
            assert result["decision"] == "unavailable" and "旧回答" not in str(result)
            entry.published_revision_id = revision.id
            entry.withdrawn_at = datetime.now(timezone.utc)
            await session.commit()
            result = await resolve_public_answer(session, poi_id="park", query="测试问题")
            assert result["decision"] == "unavailable" and "旧回答" not in str(result)
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_publish_rejects_a_reference_that_is_no_longer_current(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "stale.db"))
        try:
            session.add(GuideLoopCase(cluster_id="stale-binding", category="retrieval_gap", status="open"))
            await session.commit()
            service = GuideLoopPublicationService(session)
            payload = DraftRequest(base_revision="0", action="add_alias", poi_id="park", target_id="object", alias="问题", answer="回答", evidence={"evidence_id": "e", "source_ref": "来源"}, knowledge_entry_id=42, knowledge_revision_id="missing", effective_from="2020-01-01T00:00:00Z")
            case = await service.create_draft("stale-binding", payload)
            await session.commit()
            await service.verify("stale-binding", case.draft_id)
            await session.commit()
            with pytest.raises(ValueError, match="not currently published"):
                await service.publish("stale-binding", case.draft_id, "0", source_reviewed=True)
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())
