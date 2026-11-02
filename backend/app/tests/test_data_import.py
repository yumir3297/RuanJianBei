import asyncio
import json

import pytest

from sqlalchemy import func, select

from app.core.config import Settings
from app.models.behavior_summary import BehaviorSummary
from app.models.faq import FAQEntryRecord
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.models.route import RouteTemplate
from app.schemas.recommend import RecommendRequest
from app.services.data_import.importer import ProcessedDataImporter
from app.services.recommend.engine import RecommendEngine
from app.repositories.route import RouteRepository
from app.tests.async_db import open_test_session


def test_processed_sync_advances_visibility_epoch_in_data_transaction(tmp_path):
    from app.models.knowledge_workspace import KnowledgeState
    from app.repositories.qa_cache import QACacheRepository
    from app.services.qa.cache import QACache
    from sqlalchemy.ext.asyncio import async_sessionmaker
    db_path = tmp_path / "epoch.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", chroma_persist_dir=str(tmp_path / "index"))

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add(KnowledgeState(id=1, epoch=10))
            await session.commit()
            await ProcessedDataImporter(session, settings).sync()
            # A request that began before sync can still write its old key later.
            await QACache(QACacheRepository(session), ttl_seconds=60).set("q", "旧答案", [], epoch=10)
            async with async_sessionmaker(engine, expire_on_commit=False)() as observer:
                assert (await observer.get(KnowledgeState, 1)).epoch == 11
                assert await observer.scalar(select(func.count(FAQEntryRecord.id))) > 0
                assert await QACache(QACacheRepository(observer), ttl_seconds=60).get("q", epoch=11) is None
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_failed_processed_sync_does_not_commit_epoch_or_faq(tmp_path, monkeypatch):
    from app.models.knowledge_workspace import KnowledgeState
    from sqlalchemy.ext.asyncio import async_sessionmaker
    db_path = tmp_path / "failed-epoch.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", chroma_persist_dir=str(tmp_path / "index"))

    async def fail_before_commit(_self, _payload):
        raise RuntimeError("injected import failure")

    monkeypatch.setattr(ProcessedDataImporter, "_sync_behavior_summary", fail_before_commit)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add(KnowledgeState(id=1, epoch=10))
            await session.commit()
            with pytest.raises(RuntimeError, match="injected import failure"):
                await ProcessedDataImporter(session, settings).sync()
            await session.rollback()
            async with async_sessionmaker(engine, expire_on_commit=False)() as observer:
                assert (await observer.get(KnowledgeState, 1)).epoch == 10
                assert await observer.scalar(select(func.count(FAQEntryRecord.id))) == 0
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_processed_import_waits_for_index_writer_lock(tmp_path):
    from app.services.rag.index_write_lock import index_write_lock
    db_path = tmp_path / "locked-import.db"
    index_path = tmp_path / "index"
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False,
                        chroma_persist_dir=str(index_path), rag_collection_name="test_index")

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            async with index_write_lock(index_path / "test_index.writer.lock"):
                task = asyncio.create_task(ProcessedDataImporter(session, settings).sync())
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), 0.1)
            report = await asyncio.wait_for(task, 5)
            assert report.knowledge_imported > 0
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_processed_chunk_refresh_preserves_published_revision_history(tmp_path):
    from app.models.knowledge_workspace import KnowledgeRevision
    db_path = tmp_path / "chunk-history.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", chroma_persist_dir=str(tmp_path / "index"))

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            entry = KnowledgeEntry(title="景点", category="景点", content="当前内容", source="资料", aliases="")
            session.add(entry)
            await session.flush()
            for revision_id, content in (("old-revision", "原内容"), ("current-revision", "当前内容")):
                session.add(KnowledgeRevision(id=revision_id, knowledge_entry_id=entry.id,
                    title="景点", category="景点", content=content, source="资料"))
            await session.flush()
            entry.published_revision_id = "current-revision"
            session.add_all([
                KnowledgeChunk(chunk_id="old-fragment", source_entry_id=entry.id, revision_id="old-revision",
                    chunk_index=1, title="景点", category="景点", content="原内容", source="资料"),
                KnowledgeChunk(chunk_id="current-fragment", source_entry_id=entry.id, revision_id="current-revision",
                    chunk_index=1, title="景点", category="景点", content="当前内容", source="资料"),
            ])
            await session.commit()
            await ProcessedDataImporter(session, settings).sync()
            session.expire_all()
            assert (await session.get(KnowledgeChunk, "old-fragment")).content == "原内容"
            assert (await session.get(KnowledgeChunk, "current-fragment")).content == "当前内容"
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_processed_data_importer_syncs_all_assets(tmp_path) -> None:
    db_path = tmp_path / "importer.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            report = await ProcessedDataImporter(session, settings).sync()

            assert report.knowledge_imported == 38
            assert report.chunk_imported > report.knowledge_imported
            assert report.faq_imported == 88
            # data/processed/route_recommendations.json 现在有 7 条路线，这里原先写死的 3 已过时
            assert report.route_imported == 7
            assert report.behavior_imported == 1

            assert await session.scalar(select(func.count(KnowledgeEntry.id))) == 38
            assert await session.scalar(select(func.count(KnowledgeChunk.chunk_id))) == report.chunk_imported
            assert await session.scalar(select(func.count(FAQEntryRecord.id))) == 88
            assert await session.scalar(select(func.count(RouteTemplate.id))) == 7
            assert await session.scalar(select(func.count(BehaviorSummary.id))) == 1

            big_buddha = await session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.title == "灵山大佛"))
            assert big_buddha is not None
            assert big_buddha.published_revision_id is None
            assert big_buddha.draft_revision_id is not None
            assert big_buddha.metadata_json is not None
            big_buddha_metadata = json.loads(big_buddha.metadata_json)
            assert big_buddha_metadata["scenic_area"] == "灵山胜境"
            assert "attraction_id" in big_buddha_metadata

            big_buddha_chunk = await session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.title == "灵山大佛"))
            assert big_buddha_chunk is not None
            assert "88" in big_buddha_chunk.content
            assert big_buddha_chunk.metadata_json is not None
            chunk_metadata = json.loads(big_buddha_chunk.metadata_json)
            assert chunk_metadata["source_entry_id"] == big_buddha.id
            assert chunk_metadata["source_title"] == "灵山大佛"

            overview = await session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.title == "景区概况与千年历史渊源"))
            assert overview is not None
            assert overview.metadata_json is not None
            overview_metadata = json.loads(overview.metadata_json)
            assert overview_metadata["section_type"] == "overview"

            response = await RecommendEngine(RouteRepository(session)).generate(
                RecommendRequest(
                    session_id="recommend-test",
                    interests=["自然风光"],
                    available_hours=5,
                    audience_type="general",
                )
            )
            assert response.routes[0].route_id == "route_002"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_processed_data_sync_preserves_faq_linked_to_resolved_blind_spot(tmp_path) -> None:
    db_path = tmp_path / "preserve-admin-faq.db"
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    async def scenario():
        engine, session = await open_test_session(str(db_path))
        try:
            importer = ProcessedDataImporter(session, settings)
            await importer.sync()
            managed_source = await session.scalar(select(KnowledgeEntry.source).limit(1))
            retained = KnowledgeEntry(
                title="人工补充条目",
                category="实用贴士",
                content="这条不是数据源的一部分，不应被同步删除。",
                source=managed_source,
            )
            session.add(retained)
            session.add(
                FAQEntryRecord(
                    id="faq_admin_restroom_001",
                    category="实用信息",
                    aliases_json='["卫生间在哪里"]',
                    answer="人工核验答案",
                    sources_json='["景区运营后台人工核验"]',
                )
            )
            session.add(
                KnowledgeBlindSpot(
                    normalized_query="卫生间在哪里",
                    raw_query_samples_json='["卫生间在哪里"]',
                    hit_count=2,
                    status="resolved",
                    category="实用信息",
                    resolution_type="faq",
                    resolved_faq_id="faq_admin_restroom_001",
                )
            )
            await session.commit()

            report = await importer.sync()

            assert await session.get(KnowledgeEntry, retained.id) is not None
            preserved = await session.get(FAQEntryRecord, "faq_admin_restroom_001")
            assert report.faq_imported == 88
            assert preserved is not None
            assert preserved.answer == "人工核验答案"
            assert await session.scalar(select(func.count(FAQEntryRecord.id))) == 89
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
