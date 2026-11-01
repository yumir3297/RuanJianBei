from __future__ import annotations

import asyncio

from app.tests.async_db import open_test_session


def test_worker_can_start_attempt_while_locking_its_current_tour_session():
    async def scenario():
        from app.repositories.tool_execution import ToolExecutionRepository
        from app.repositories.tour_session import TourSessionRepository

        engine, db = await open_test_session()
        try:
            session = await TourSessionRepository(db).create_session(
                "owner-a", "site", "验收游览",
                {"schema_version": 2, "constraints": {}, "stops": [], "legs": [],
                 "source": "manual", "source_references": []},
                "session-create",
            )
            repo = ToolExecutionRepository(db)
            queued = await repo.create_job(
                principal_type="tourist", principal_id="owner-a", site_id="site",
                tool_name="smoke.handler", tool_version="1", workflow_schema_version="1",
                recovery_mode="manual_retry", retry_safe=False,
                target={"type": "tour_session", "id": session["id"], "base_revision": 1,
                        "progress_version": 0},
                payload={"request": "smoke"}, idempotency_key="job-create",
                deadline_seconds=300, max_attempts=1,
            )

            lease = await repo.claim_next("smoke-worker", lease_seconds=30)
            assert lease is not None and lease.job_id == queued["id"]
            assert await repo.start_attempt(lease, max_attempts=1)

            running = await repo.get_job(
                "tourist", "owner-a", "site", session["id"], queued["id"],
            )
            assert running is not None
            assert running["status"] == "running"
            assert running["steps"][0]["status"] == "running"
        finally:
            await db.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_proposal_api_replays_same_request_and_conflicts_on_changed_payload(monkeypatch):
    async def scenario():
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from app.api import tour_sessions
        from app.core.config import Settings
        from app.core.deps import get_app_settings, get_db_session
        from app.repositories.tour_session import TourSessionRepository
        from app.schemas.itinerary import TourSnapshotV2
        from app.services.itinerary.catalog import CatalogSnapshot, PublishedAttractionCatalog
        from app.services.itinerary.intent import snapshot_digest

        engine, first_db = await open_test_session()
        await first_db.close()
        sessions = async_sessionmaker(bind=engine, expire_on_commit=False)
        catalog = CatalogSnapshot(site_id="site", entries=(), digest="c" * 64)

        async def fake_catalog(_self, _site_id):
            return catalog

        monkeypatch.setattr(PublishedAttractionCatalog, "list_for_site", fake_catalog)
        app = FastAPI()
        app.include_router(tour_sessions.router, prefix="/api/tour-sessions")

        async def db_dependency():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_db_session] = db_dependency
        app.dependency_overrides[get_app_settings] = lambda: Settings(
            site_id="site", admin_token_secret="proposal-replay-test-secret",
        )
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                bootstrap = await client.get("/api/tour-sessions/bootstrap")
                assert bootstrap.status_code == 200
                identity_id = bootstrap.json()["identity_id"]
                csrf = bootstrap.json()["csrf_token"]
                snapshot = TourSnapshotV2()
                async with sessions() as db:
                    created = await TourSessionRepository(db).create_session(
                        identity_id, "site", "验收游览", snapshot.model_dump(mode="json"), "fixture-create",
                    )

                payload = {
                    "expected_version": 1,
                    "progress_version": 0,
                    "draft_digest": snapshot_digest(snapshot),
                    "draft_snapshot": snapshot.model_dump(mode="json"),
                    "text": "缩短游览时间",
                }
                headers = {
                    "Origin": "http://testserver",
                    "X-CSRF-Token": csrf,
                    "Idempotency-Key": "proposal-api-replay",
                }
                path = f"/api/tour-sessions/{created['id']}/proposals"
                first = await client.post(path, headers=headers, json=payload)
                assert first.status_code == 202, first.text

                replay = await client.post(path, headers=headers, json=payload)
                assert replay.status_code == 202, replay.text
                assert replay.json()["id"] == first.json()["id"]
                assert replay.json()["execution_job_id"] == first.json()["execution_job_id"]

                summaries = await client.get(path)
                assert summaries.status_code == 200, summaries.text
                assert summaries.json()["items"][0]["request_text"] == payload["text"]
                assert summaries.headers.get("cache-control") == "no-store"
                detail = await client.get(f"{path}/{first.json()['id']}")
                assert detail.status_code == 200, detail.text
                assert detail.headers.get("cache-control") == "no-store"
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as stranger:
                    await stranger.get("/api/tour-sessions/bootstrap")
                    denied = await stranger.get(path)
                    assert denied.status_code == 404
                    assert payload["text"] not in denied.text

                conflict = await client.post(path, headers=headers, json={**payload, "text": "不同需求"})
                assert conflict.status_code == 409, conflict.text

                # Inject a failure after enqueue has flushed its rows: the proposal,
                # job and their idempotency records must all roll back together.
                from sqlalchemy import func, select
                from app.models.tour_session import ItineraryProposal
                from app.models.tool_execution import ToolJob
                from app.repositories.tool_execution import JobCommandError
                original_enqueue = tour_sessions.enqueue_registered_tool

                async def fail_after_enqueue(*args, **kwargs):
                    await original_enqueue(*args, **kwargs)
                    raise JobCommandError("injected enqueue failure")

                monkeypatch.setattr(tour_sessions, "enqueue_registered_tool", fail_after_enqueue)
                failed_headers = {**headers, "Idempotency-Key": "rollback-key"}
                failed = await client.post(path, headers=failed_headers, json=payload)
                assert failed.status_code == 409
                async with sessions() as check:
                    assert await check.scalar(select(func.count()).select_from(ItineraryProposal)) == 1
                    assert await check.scalar(select(func.count()).select_from(ToolJob)) == 1
                monkeypatch.setattr(tour_sessions, "enqueue_registered_tool", original_enqueue)
                recovered = await client.post(path, headers=failed_headers, json=payload)
                assert recovered.status_code == 202, recovered.text
                assert recovered.json()["id"] != first.json()["id"]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


async def _queued_fixture(db):
    from app.repositories.tool_execution import ToolExecutionRepository
    from app.repositories.tour_session import TourSessionRepository
    from app.schemas.itinerary import TourSnapshotV2

    tours = TourSessionRepository(db)
    snapshot = TourSnapshotV2().model_dump(mode="json")
    tour = await tours.create_session("owner-a", "site", "执行验收", snapshot, "create")
    tools = ToolExecutionRepository(db)
    job = await tools.create_job(
        principal_type="tourist", principal_id="owner-a", site_id="site",
        tool_name="test.handler", tool_version="1", workflow_schema_version="1",
        recovery_mode="manual_retry", retry_safe=False,
        target={"type": "tour_session", "id": tour["id"], "base_revision": 1, "progress_version": 0},
        payload={"test": True}, idempotency_key="queued", deadline_seconds=300, max_attempts=1,
    )
    return tours, tools, tour, job, snapshot


def test_changed_target_invalidates_running_lease_and_blocks_late_result():
    async def scenario():
        engine, db = await open_test_session()
        try:
            tours, tools, tour, job, snapshot = await _queued_fixture(db)
            lease = await tools.claim_next("worker", lease_seconds=30)
            assert await tools.start_attempt(lease, max_attempts=1)
            snapshot["constraints"]["available_minutes"] = 45
            await tours.save_revision("owner-a", tour["id"], 1, snapshot, "edit")
            assert not await tools.complete_execution(lease, {"late": True})
            current = await tools.get_job("tourist", "owner-a", "site", tour["id"], job["id"])
            assert current["status"] == "stale"
            assert (await tours.get_session("owner-a", tour["id"]))["version"] == 2
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_wrong_fence_cannot_complete_current_worker_job():
    async def scenario():
        from dataclasses import replace
        engine, db = await open_test_session()
        try:
            _tours, tools, tour, job, _snapshot = await _queued_fixture(db)
            lease = await tools.claim_next("worker", lease_seconds=30)
            assert await tools.start_attempt(lease, max_attempts=1)
            assert not await tools.complete_execution(replace(lease, fence=lease.fence - 1), {"wrong": True})
            assert await tools.complete_execution(lease, {"correct": True})
            current = await tools.get_job("tourist", "owner-a", "site", tour["id"], job["id"])
            assert current["status"] == "succeeded"
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_unknown_external_result_requires_explicit_retry_confirmation():
    async def scenario():
        import pytest
        from app.repositories.tool_execution import JobCommandError
        engine, db = await open_test_session()
        try:
            _tours, tools, tour, job, _snapshot = await _queued_fixture(db)
            lease = await tools.claim_next("worker", lease_seconds=30)
            assert await tools.start_attempt(lease, max_attempts=1)
            assert await tools.mark_external_call(lease)
            assert await tools.fail_step(lease, "provider_unavailable", retryable=True, external_outcome="unknown")
            assert await tools.claim_next("automatic-retry") is None
            with pytest.raises(JobCommandError, match="确认"):
                await tools.manual_retry("tourist", "owner-a", "site", tour["id"], job["id"], "retry-no", False)
            await db.rollback()
            retried = await tools.manual_retry("tourist", "owner-a", "site", tour["id"], job["id"], "retry-yes", True)
            assert retried["status"] == "queued"
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_cancel_waiting_user_closes_step_and_preserves_unknown_outcome():
    async def scenario():
        from sqlalchemy import select
        from app.models.tool_execution import ToolAttempt, ToolStep
        engine, db = await open_test_session()
        try:
            _tours, tools, tour, job, _snapshot = await _queued_fixture(db)
            lease = await tools.claim_next("worker")
            assert await tools.start_attempt(lease, max_attempts=1)
            assert await tools.mark_external_call(lease)
            assert await tools.fail_step(lease, "timeout", retryable=False, external_outcome="unknown")
            cancelled = await tools.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "cancel-unknown")
            assert cancelled["status"] == "cancelled"
            assert cancelled["reason"] == "cancelled_external_outcome_unknown"
            assert cancelled["steps"][0]["status"] == "cancelled"
            step = await db.scalar(select(ToolStep).where(ToolStep.job_id == job["id"]))
            attempt = await db.scalar(select(ToolAttempt).where(ToolAttempt.step_id == step.id))
            assert step.external_state == "unknown"
            assert attempt.outcome == "unknown" and attempt.external_state == "unknown"
            assert await tools.claim_next("other") is None
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_cancel_racing_external_marker_preserves_unknown(tmp_path):
    async def scenario():
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.repositories.tool_execution import ToolExecutionRepository
        engine, db = await open_test_session(str(tmp_path / "race.sqlite"))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            _, tools, tour, job, _ = await _queued_fixture(db)
            lease = await tools.claim_next("worker")
            assert await tools.start_attempt(lease, max_attempts=1)
            async with sessions() as cancel_db, sessions() as marker_db:
                seen, resume = asyncio.Event(), asyncio.Event()
                original = cancel_db.execute
                async def paused(statement, *args, **kwargs):
                    if "UPDATE tool_jobs" in str(statement) and not seen.is_set():
                        seen.set()
                        await resume.wait()
                    return await original(statement, *args, **kwargs)
                cancel_db.execute = paused
                cancel = asyncio.create_task(ToolExecutionRepository(cancel_db).request_cancel(
                    "tourist", "owner-a", "site", tour["id"], job["id"], "race-cancel"))
                await asyncio.wait_for(seen.wait(), 2)
                assert await ToolExecutionRepository(marker_db).mark_external_call(lease)
                resume.set()
                result = await cancel
                assert result["reason"] == "cancelled_external_outcome_unknown"
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_cancel_cas_conflict_can_retry_same_key_after_unknown(tmp_path):
    async def scenario():
        import pytest
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.repositories.tool_execution import ToolExecutionRepository, IdempotencyConflict
        engine, db = await open_test_session(str(tmp_path / "cancel-cas.sqlite"))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            _, tools, tour, job, _ = await _queued_fixture(db)
            lease = await tools.claim_next("worker")
            assert await tools.start_attempt(lease, max_attempts=1)
            assert await tools.mark_external_call(lease)
            async with sessions() as a, sessions() as b:
                seen, resume = asyncio.Event(), asyncio.Event()
                original = a.execute
                async def pause(stmt, *args, **kwargs):
                    if "UPDATE tool_jobs" in str(stmt) and not seen.is_set():
                        seen.set()
                        await resume.wait()
                    return await original(stmt, *args, **kwargs)
                a.execute = pause
                repo = ToolExecutionRepository(a)
                task = asyncio.create_task(repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "same-key"))
                await asyncio.wait_for(seen.wait(), 2)
                assert await ToolExecutionRepository(b).fail_step(lease, "timeout", retryable=False, external_outcome="unknown")
                resume.set()
                with pytest.raises(IdempotencyConflict):
                    await task
                result = await repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "same-key")
                assert result["status"] == "cancelled"
                assert result["reason"] == "cancelled_external_outcome_unknown"
                assert result["steps"][0]["status"] == "cancelled"
                replay = await repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "same-key")
                assert replay["status"] == "cancelled" and replay["reason"] == result["reason"]
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_cancel_cas_conflict_with_completion_can_retry_same_key(tmp_path):
    async def scenario():
        import pytest
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.repositories.tool_execution import ToolExecutionRepository, IdempotencyConflict
        engine, db = await open_test_session(str(tmp_path / "terminal-cas.sqlite"))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            _, tools, tour, job, _ = await _queued_fixture(db)
            lease = await tools.claim_next("worker")
            assert await tools.start_attempt(lease, max_attempts=1)
            async with sessions() as a, sessions() as b:
                seen, resume = asyncio.Event(), asyncio.Event()
                original = a.execute
                async def pause(stmt, *args, **kwargs):
                    if "UPDATE tool_jobs" in str(stmt) and not seen.is_set():
                        seen.set()
                        await resume.wait()
                    return await original(stmt, *args, **kwargs)
                a.execute = pause
                repo = ToolExecutionRepository(a)
                task = asyncio.create_task(repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "terminal-key"))
                await asyncio.wait_for(seen.wait(), 2)
                assert await ToolExecutionRepository(b).complete_execution(lease, {"value": 42})
                resume.set()
                with pytest.raises(IdempotencyConflict):
                    await task
                result = await repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "terminal-key")
                assert result["status"] == "succeeded"
                replay = await repo.request_cancel("tourist", "owner-a", "site", tour["id"], job["id"], "terminal-key")
                assert replay["status"] == "succeeded"
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())
