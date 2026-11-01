"""Opt-in integration check against a disposable, migrated local PostgreSQL DB."""
import asyncio
import os
import select
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy import select as sql_select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.tour_session import TourIdentity
from app.models.tool_execution import ToolJob
from app.repositories.tool_execution import ToolExecutionRepository
from app.repositories.tour_session import TourSessionRepository
from app.schemas.itinerary import TourSnapshotV2
from app.tests.test_w02_runtime_review import expire_lease


@pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")
@pytest.mark.parametrize("external_started", [False, True], ids=["before-external", "external-unknown"])
def test_two_worker_processes_do_not_claim_the_same_job(external_started):
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")

    async def setup():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner = str(uuid4())
        try:
            async with sessions() as session:
                session.add(TourIdentity(id=owner, credential_digest=uuid4().hex,
                                         expires_at=datetime.now(UTC) + timedelta(days=1)))
                await session.commit()
                tour = await TourSessionRepository(session).create_session(
                    owner, "pg-test-site", "process claim", TourSnapshotV2().model_dump(mode="json"), "create")
                job = await ToolExecutionRepository(session).create_job(
                    principal_type="tourist", principal_id=owner, site_id="pg-test-site",
                    tool_name="test.fake", tool_version="1", workflow_schema_version="1",
                    retry_safe=False, max_attempts=1, recovery_mode="manual_retry",
                    target={"type": "tour_session", "id": tour["id"], "base_revision": 1, "progress_version": 0},
                    payload={}, idempotency_key="create-job", deadline_seconds=300)
                return job["id"]
        finally:
            await engine.dispose()

    job_id = asyncio.run(setup())
    script = '''
import asyncio, os, sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.repositories.tool_execution import ToolExecutionRepository
async def main():
    engine = create_async_engine(os.environ["GUIDE_TEST_POSTGRES_URL"])
    try:
        sys.stdin.readline()
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            repo = ToolExecutionRepository(session)
            lease = await repo.claim_next(sys.argv[1])
            if lease:
                assert await repo.start_attempt(lease, max_attempts=1)
                if sys.argv[2] == "yes":
                    assert await repo.mark_external_call(lease)
            print(f"{lease.job_id}:{lease.fence}" if lease else "none", flush=True)
            if lease:
                await asyncio.sleep(60)
    finally:
        await engine.dispose()
asyncio.run(main())
'''
    workers = [subprocess.Popen([sys.executable, "-c", script, f"process-{index}", "yes" if external_started else "no"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
               for index in range(2)]
    try:
        for worker in workers:
            worker.stdin.write("start\n")
            worker.stdin.flush()
        outputs = []
        for worker in workers:
            readable, _, _ = select.select([worker.stdout], [], [], 15)
            assert readable, "worker did not report its claim"
            outputs.append(worker.stdout.readline().strip())
        claimed = [value for value in outputs if value != "none"]
        assert len(claimed) == 1 and outputs.count("none") == 1
        claimed_job, old_fence = claimed[0].split(":")
        assert claimed_job == job_id
        claimant = workers[outputs.index(claimed[0])]
        claimant.kill()
        claimant.communicate(timeout=5)

        async def recover():
            engine = create_async_engine(url)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with sessions() as session:
                    await expire_lease(session, job_id)
                    await ToolExecutionRepository(session).maintain()
                    lease = await ToolExecutionRepository(session).claim_next("replacement-process")
                    if external_started:
                        assert lease is None
                        job = await session.scalar(sql_select(ToolJob).where(ToolJob.id == job_id))
                        assert job.status == "waiting_user"
                    else:
                        assert lease is not None and lease.job_id == job_id and lease.fence > int(old_fence)
                        assert await ToolExecutionRepository(session).start_attempt(lease, max_attempts=1)
            finally:
                await engine.dispose()
        asyncio.run(recover())
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.communicate()


@pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")
def test_postgres_job_foreign_keys_claim_and_fencing():
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    # Never run this mutating integration test against an arbitrary database.
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")

    async def scenario():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner = str(uuid4())
        try:
            async with sessions() as session:
                session.add(TourIdentity(id=owner, credential_digest=uuid4().hex,
                    expires_at=datetime.now(UTC) + timedelta(days=1)))
                await session.commit()
                tour = await TourSessionRepository(session).create_session(
                    owner, "pg-test-site", "PostgreSQL integration test",
                    TourSnapshotV2().model_dump(mode="json"), "create-tour")
                job = await ToolExecutionRepository(session).create_job(
                    principal_type="tourist", principal_id=owner, site_id="pg-test-site",
                    tool_name="test.fake", tool_version="1", workflow_schema_version="1",
                    retry_safe=False, max_attempts=1, recovery_mode="manual_retry",
                    target={"type": "tour_session", "id": tour["id"],
                            "base_revision": 1, "progress_version": 0},
                    payload={"value": 42}, idempotency_key="create-job", deadline_seconds=300)

            async def claim(name):
                async with sessions() as session:
                    return await ToolExecutionRepository(session).claim_next(name)

            claims = await asyncio.gather(claim("pg-worker-a"), claim("pg-worker-b"))
            assert sum(claim is not None for claim in claims) == 1
            old = next(claim for claim in claims if claim is not None)
            async with sessions() as session:
                await expire_lease(session, job["id"])
                await ToolExecutionRepository(session).maintain()
            new = await claim("pg-worker-c")
            assert new is not None and new.fence > old.fence
            async with sessions() as session:
                assert not await ToolExecutionRepository(session).complete_execution(old, {"value": 0})
                repo = ToolExecutionRepository(session)
                assert await repo.start_attempt(new, max_attempts=1)
                assert await repo.mark_external_call(new)

            async def cancel():
                async with sessions() as session:
                    return await ToolExecutionRepository(session).request_cancel(
                        "tourist", owner, "pg-test-site", tour["id"], job["id"], "cancel-job")

            async def complete():
                async with sessions() as session:
                    return await ToolExecutionRepository(session).complete_execution(new, {"value": 42})

            cancelled_view, completed = await asyncio.wait_for(
                asyncio.gather(cancel(), complete()), timeout=10)
            async with sessions() as session:
                final = await ToolExecutionRepository(session).get_job(
                    "tourist", owner, "pg-test-site", tour["id"], job["id"])
            assert final["status"] in ("cancelled", "succeeded")
            assert cancelled_view["status"] == final["status"]
            assert completed == (final["status"] == "succeeded")
            assert final["steps"][0]["status"] == final["status"]
            if final["status"] == "cancelled":
                assert final["reason"] == "cancelled_external_outcome_unknown"
                assert final["result"] is None
        finally:
            await engine.dispose()

    asyncio.run(scenario())
