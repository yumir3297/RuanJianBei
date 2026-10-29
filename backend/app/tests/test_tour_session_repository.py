from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from app.tests.async_db import open_test_session


def _run(scenario):
    asyncio.run(scenario())


def test_create_and_save_revision_keeps_prior_snapshot_immutable():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            first_payload = {"constraints": {"available_minutes": 180}, "stops": []}
            created = await repo.create_session("owner-a", "default", "Family visit", first_payload, "create-1")
            saved = await repo.save_revision("owner-a", created["id"], 1,
                                              {"constraints": {"available_minutes": 150}, "stops": []}, "save-1")
            history = await repo.list_revisions("owner-a", created["id"])
            current = await repo.get_session("owner-a", created["id"])
            assert created["version"] == 1
            assert saved["version"] == 2
            assert current["snapshot"]["constraints"]["available_minutes"] == 150
            assert [item["snapshot"]["constraints"]["available_minutes"] for item in history] == [180, 150]
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_stale_version_conflicts_without_writing_a_revision():
    async def scenario():
        from app.repositories.tour_session import RevisionConflict, TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "default", "Trip", {}, "create-1")
            await repo.save_revision("owner-a", created["id"], 1, {"stops": ["佛足坛"]}, "save-1")
            try:
                await repo.save_revision("owner-a", created["id"], 1, {"stops": ["灵山大佛"]}, "save-2")
            except RevisionConflict as error:
                assert error.current_version == 2
            else:
                raise AssertionError("stale revision must conflict")
            assert len(await repo.list_revisions("owner-a", created["id"])) == 2
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_idempotent_create_replays_result_and_rejects_changed_payload():
    async def scenario():
        from app.repositories.tour_session import IdempotencyConflict, TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            first = await repo.create_session("owner-a", "default", "Trip", {}, "same-key")
            replay = await repo.create_session("owner-a", "default", "Trip", {}, "same-key")
            assert replay == first
            try:
                await repo.create_session("owner-a", "default", "Different", {}, "same-key")
            except IdempotencyConflict:
                pass
            else:
                raise AssertionError("same key with different body must conflict")
            assert len(await repo.list_sessions("owner-a")) == 1
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_other_owner_cannot_read_or_mutate_session():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "default", "Private", {}, "create-1")
            assert await repo.get_session("owner-b", created["id"]) is None
            assert await repo.delete_session("owner-b", created["id"], 1) is None
            assert len(await repo.list_sessions("owner-a")) == 1
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_soft_delete_restore_and_purge_preserve_revision_history_rules():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "default", "Trip", {"stops": ["佛足坛"]}, "create-1")
            deleted = await repo.delete_session("owner-a", created["id"], 1)
            assert deleted["version"] == 2
            assert await repo.get_session("owner-a", created["id"]) is None
            assert len(await repo.list_trash("owner-a")) == 1
            restored = await repo.undelete_session("owner-a", created["id"])
            assert restored["version"] == 3
            assert restored["snapshot"]["stops"] == ["佛足坛"]
            await repo.delete_session("owner-a", created["id"], 3)
            assert await repo.purge_session("owner-a", created["id"])
            assert await repo.get_session("owner-a", created["id"]) is None
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_restore_old_revision_creates_a_new_immutable_revision():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "default", "Trip", {"stops": ["佛足坛"]}, "create-1")
            saved = await repo.save_revision("owner-a", created["id"], 1, {"stops": ["灵山大佛"]}, "save-1")
            history = await repo.list_revisions("owner-a", created["id"])
            restored = await repo.restore_revision("owner-a", created["id"], history[0]["id"], 2, "restore-1")
            assert restored["version"] == 3
            assert restored["snapshot"]["stops"] == ["佛足坛"]
            assert (await repo.get_session("owner-a", created["id"]))["snapshot"]["stops"] == ["佛足坛"]
            assert (await repo.list_revisions("owner-a", created["id"]))[1]["snapshot"]["stops"] == ["灵山大佛"]
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)


def test_expired_trash_cannot_be_restored_and_expired_idempotency_is_reusable():
    async def scenario():
        from app.models.tour_session import TourSession, TourSessionIdempotency
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "default", "Trip", {}, "create-1")
            await repo.delete_session("owner-a", created["id"], 1)
            await db.execute(update(TourSession).where(TourSession.id == created["id"]).values(
                deleted_until=datetime.now(UTC) - timedelta(seconds=1)
            ))
            await db.commit()
            assert await repo.list_trash("owner-a") == []
            assert await repo.undelete_session("owner-a", created["id"]) is None

            await db.execute(update(TourSessionIdempotency).where(
                TourSessionIdempotency.key == "expired-key"
            ).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
            await db.commit()
            retried = await repo.create_session("owner-a", "default", "Changed", {}, "expired-key")
            assert retried["title"] == "Changed"
        finally:
            await db.close()
            await engine.dispose()
    _run(scenario)
