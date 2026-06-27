import json

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
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


def test_processed_data_importer_syncs_all_assets(tmp_path) -> None:
    db_path = tmp_path / "importer.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    session = session_local()
    try:
        report = ProcessedDataImporter(session, settings).sync()

        assert report.knowledge_imported == 38
        assert report.chunk_imported > report.knowledge_imported
        assert report.faq_imported == 88
        assert report.route_imported == 3
        assert report.behavior_imported == 1

        assert session.scalar(select(func.count(KnowledgeEntry.id))) == 38
        assert session.scalar(select(func.count(KnowledgeChunk.chunk_id))) == report.chunk_imported
        assert session.scalar(select(func.count(FAQEntryRecord.id))) == 88
        assert session.scalar(select(func.count(RouteTemplate.id))) == 3
        assert session.scalar(select(func.count(BehaviorSummary.id))) == 1

        big_buddha = session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.title == "灵山大佛"))
        assert big_buddha is not None
        assert big_buddha.metadata_json is not None
        big_buddha_metadata = json.loads(big_buddha.metadata_json)
        assert big_buddha_metadata["scenic_area"] == "灵山胜境"
        assert "attraction_id" in big_buddha_metadata

        big_buddha_chunk = session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.title == "灵山大佛"))
        assert big_buddha_chunk is not None
        assert "88" in big_buddha_chunk.content
        assert big_buddha_chunk.metadata_json is not None
        chunk_metadata = json.loads(big_buddha_chunk.metadata_json)
        assert chunk_metadata["source_entry_id"] == big_buddha.id
        assert chunk_metadata["source_title"] == "灵山大佛"

        overview = session.scalar(select(KnowledgeEntry).where(KnowledgeEntry.title == "景区概况与千年历史渊源"))
        assert overview is not None
        assert overview.metadata_json is not None
        overview_metadata = json.loads(overview.metadata_json)
        assert overview_metadata["section_type"] == "overview"

        response = RecommendEngine(RouteRepository(session)).generate(
            RecommendRequest(
                session_id="recommend-test",
                interests=["自然风光"],
                available_hours=5,
                audience_type="general",
            )
        )
        assert response.routes[0].route_id == "route_002"
    finally:
        session.close()


def test_processed_data_sync_preserves_faq_linked_to_resolved_blind_spot(tmp_path) -> None:
    db_path = tmp_path / "preserve-admin-faq.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    settings = Settings(database_url=f"sqlite:///{db_path}", enable_sample_data=False)

    session = session_local()
    try:
        importer = ProcessedDataImporter(session, settings)
        importer.sync()
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
        session.commit()

        report = importer.sync()

        preserved = session.get(FAQEntryRecord, "faq_admin_restroom_001")
        assert report.faq_imported == 88
        assert preserved is not None
        assert preserved.answer == "人工核验答案"
        assert session.scalar(select(func.count(FAQEntryRecord.id))) == 89
    finally:
        session.close()
