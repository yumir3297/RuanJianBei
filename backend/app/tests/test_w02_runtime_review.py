"""Isolated W02 review: all providers are fake; no production database or network."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.tool_execution import ToolJob
from app.repositories.tool_execution import ToolExecutionRepository
from app.repositories.tour_session import TourSessionRepository
from app.schemas.itinerary import TourSnapshotV2
from app.services.tool_execution.registry import ToolHandler, ToolRegistry
from app.services.tool_execution.runner import ToolRunner
from app.tests.async_db import open_test_session


class FakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int


def fake_registry(calls):
    async def execute(payload, _context):
        calls.append(payload.value)
        return payload
    registry = ToolRegistry()
    registry.register(ToolHandler(
        name="review.fake", version="1", workflow_schema_version="1",
        input_model=FakePayload, output_model=FakePayload, execute=execute,
        retry_safe=False, max_attempts=1, recovery_mode="manual_retry",
    ))
    return registry


async def queued(db):
    tour = await TourSessionRepository(db).create_session(
        "review-owner", "review-site", "FAKE runtime review",
        TourSnapshotV2().model_dump(mode="json"), "create-tour",
    )
    repo = ToolExecutionRepository(db)
    job = await repo.create_job(
        principal_type="tourist", principal_id="review-owner", site_id="review-site",
        tool_name="review.fake", tool_version="1", workflow_schema_version="1",
        retry_safe=False, max_attempts=1, recovery_mode="manual_retry",
        target={"type": "tour_session", "id": tour["id"], "base_revision": 1, "progress_version": 0},
        payload={"value": 42}, idempotency_key="create-job", deadline_seconds=300,
    )
    return repo, tour, job


async def expire_lease(db, job_id):
    await db.execute(update(ToolJob).where(ToolJob.id == job_id).values(
        lease_until=datetime.now(UTC) - timedelta(seconds=1),
    ))
    await db.commit()


def test_fake_worker_serve_once_processes_queue_and_scopes_result(monkeypatch, tmp_path):
    async def scenario():
        from app.services.tool_execution import worker
        engine, db = await open_test_session(str(tmp_path / "runtime.sqlite"))
        try:
            repo, tour, job = await queued(db)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            calls = []
            monkeypatch.setattr(worker, "AsyncSessionLocal", sessions)
            monkeypatch.setattr(worker, "build_registry", lambda: fake_registry(calls))
            await worker.serve("FAKE-review-worker", once=True)
            current = await repo.get_job("tourist", "review-owner", "review-site", tour["id"], job["id"])
            assert current["status"] == "succeeded" and calls == [42]
            assert await repo.get_job("tourist", "other-owner", "review-site", tour["id"], job["id"]) is None
            assert await repo.get_job("tourist", "review-owner", "other-site", tour["id"], job["id"]) is None
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_cancel_running_external_call_fences_late_completion(tmp_path):
    async def scenario():
        engine, db = await open_test_session(str(tmp_path / "cancel.sqlite"))
        try:
            repo, tour, job = await queued(db)
            lease = await repo.claim_next("old-worker")
            assert await repo.start_attempt(lease, max_attempts=1)
            assert await repo.mark_external_call(lease)
            cancelled = await repo.request_cancel(
                "tourist", "review-owner", "review-site", tour["id"], job["id"], "cancel",
            )
            assert cancelled["status"] == "cancelled"
            assert cancelled["reason"] == "cancelled_external_outcome_unknown"
            assert not await repo.complete_execution(lease, {"value": 42})
            assert await repo.claim_next("new-worker") is None
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_restart_before_attempt_recovers_queue_with_new_fence(tmp_path):
    async def scenario():
        engine, db = await open_test_session(str(tmp_path / "recovery.sqlite"))
        try:
            repo, tour, job = await queued(db)
            old = await repo.claim_next("crashed-worker")
            await expire_lease(db, job["id"])
            await repo.maintain()
            assert not await repo.complete_execution(old, {"value": 0})
            calls = []
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            assert await ToolRunner(sessions, fake_registry(calls)).run_one("replacement-worker")
            current = await repo.get_job("tourist", "review-owner", "review-site", tour["id"], job["id"])
            assert current["status"] == "succeeded" and calls == [42]
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_restart_after_attempt_before_external_call_is_recoverable(tmp_path):
    async def scenario():
        engine, db = await open_test_session(str(tmp_path / "pre-provider.sqlite"))
        try:
            repo, tour, job = await queued(db)
            lease = await repo.claim_next("crashed-worker")
            assert await repo.start_attempt(lease, max_attempts=1)
            # No mark_external_call: no provider request has been sent.
            await expire_lease(db, job["id"])
            await repo.maintain()
            calls = []
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            assert await ToolRunner(sessions, fake_registry(calls)).run_one("replacement-worker")
            current = await repo.get_job("tourist", "review-owner", "review-site", tour["id"], job["id"])
            assert current["status"] == "succeeded", (current["status"], current["reason"], calls)
            assert calls == [42]
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize("dispose_engine", [
    True,
    False,
])
def test_worker_cli_once_reads_explicit_isolated_database(tmp_path, dispose_engine):
    async def scenario():
        import os
        import sys
        from pathlib import Path
        engine, db = await open_test_session(str(tmp_path / "cli.sqlite"))
        try:
            repo, tour, job = await queued(db)
            backend = Path(__file__).resolve().parents[2]
            # Minimal environment and a clean cwd: never read a project's .env.
            if dispose_engine:
                command = [sys.executable, "-c", "\n".join([
                    "import asyncio",
                    "from app.services.tool_execution.worker import serve",
                    "from app.db.session import engine",
                    "async def run():",
                    "    try: await serve('isolated-review-cli', once=True)",
                    "    finally: await engine.dispose()",
                    "asyncio.run(run())",
                ])]
            else:
                command = [sys.executable, "-m", "app.services.tool_execution.worker", "--once",
                           "--worker-id", "isolated-review-cli"]
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(tmp_path), env={
                    "PATH": os.defpath, "PYTHONPATH": str(backend),
                    "DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path / 'cli.sqlite'}",
                    "LLM_PROVIDER": "stub", "ASR_PROVIDER": "stub", "VISION_PROVIDER": "stub",
                }, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            communication = asyncio.create_task(process.communicate())
            timed_out = False
            try:
                stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), timeout=5)
            except asyncio.TimeoutError:
                timed_out = True
                process.kill()
                stdout, stderr = await communication
            current = await repo.get_job("tourist", "review-owner", "review-site", tour["id"], job["id"])
            # A real separate worker reached this exact isolated DB and rejected
            # the intentionally unregistered FAKE handler without provider use.
            assert current["status"] == "failed"
            assert current["reason"] == "handler_version_unsupported"
            assert not timed_out, "job processed, but --once did not exit within 5s"
            assert process.returncode == 0, (stdout.decode(), stderr.decode())
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())
