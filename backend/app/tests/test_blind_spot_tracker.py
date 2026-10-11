import asyncio

from sqlalchemy import select

from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.services.qa.blind_spot_tracker import BlindSpotTracker
from app.tests.async_db import open_test_session


def test_tracker_aggregates_queries_and_limits_unique_samples(tmp_path) -> None:
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "blind-spots.db"))
        try:
            tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session), sample_limit=5)
            await tracker.record(raw_query="卫生间在哪里", normalized_query="卫生间在哪里")
            await tracker.record(raw_query="卫生间在哪里", normalized_query="卫生间在哪里")
            for index in range(1, 6):
                await tracker.record(raw_query=f"第{index}种问法", normalized_query="卫生间在哪里")

            entry = await session.scalar(select(KnowledgeBlindSpot))
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
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_tracker_bounds_long_normalized_query_with_stable_hash(tmp_path) -> None:
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "long-query.db"))
        try:
            tracker = BlindSpotTracker(KnowledgeBlindSpotRepository(session))
            first = await tracker.record(raw_query="长问题", normalized_query="问" * 1000)
            second = await tracker.record(raw_query="另一种长问法", normalized_query="问" * 1000)

            assert first.id == second.id
            assert len(second.normalized_query) == 499
            assert second.hit_count == 2
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
