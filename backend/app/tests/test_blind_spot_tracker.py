from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.services.qa.blind_spot_tracker import BlindSpotTracker


def test_tracker_aggregates_queries_and_limits_unique_samples(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'blind-spots.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    session = session_local()
    try:
        tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session), sample_limit=5)
        tracker.record(raw_query="卫生间在哪里", normalized_query="卫生间在哪里")
        tracker.record(raw_query="卫生间在哪里", normalized_query="卫生间在哪里")
        for index in range(1, 6):
            tracker.record(raw_query=f"第{index}种问法", normalized_query="卫生间在哪里")

        entry = session.scalar(select(KnowledgeBlindSpot))
        assert entry is not None
        assert entry.hit_count == 7
        assert KnowledgeBlindSpotRepository.load_samples(entry.raw_query_samples_json) == [
            "第1种问法",
            "第2种问法",
            "第3种问法",
            "第4种问法",
            "第5种问法",
        ]
        assert entry.status == "open"
        assert entry.category == "unknown"
    finally:
        session.close()


def test_tracker_bounds_long_normalized_query_with_stable_hash(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'long-query.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    session = session_local()
    try:
        tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session))
        first = tracker.record(raw_query="长问题", normalized_query="问" * 1000)
        second = tracker.record(raw_query="另一种长问法", normalized_query="问" * 1000)

        assert first.id == second.id
        assert len(second.normalized_query) == 499
        assert second.hit_count == 2
    finally:
        session.close()
