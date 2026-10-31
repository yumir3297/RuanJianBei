"""Opt-in integration check against a disposable, migrated local PostgreSQL DB."""
import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.tour_session import TourIdentity
from app.repositories.tool_execution import ToolExecutionRepository
from app.repositories.tour_session import TourSessionRepository
from app.schemas.itinerary import TourSnapshotV2
from app.tests.test_w02_runtime_review import expire_lease


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
