from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import tour_sessions
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.tests.async_db import open_test_session


def test_budget_endpoint_accepts_explicit_current_stop_remaining_minutes():
    async def scenario():
        engine, first_db = await open_test_session()
        await first_db.close()
        sessions = async_sessionmaker(bind=engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(tour_sessions.router, prefix="/api/tour-sessions")

        async def db_dependency():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_db_session] = db_dependency
        app.dependency_overrides[get_app_settings] = lambda: Settings(
            site_id="lingshan", admin_token_secret="tour-session-test-secret",
        )
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                csrf = (await client.get("/api/tour-sessions/bootstrap")).json()["csrf_token"]
                write_headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}
                created = await client.post("/api/tour-sessions", headers={
                    **write_headers, "Idempotency-Key": "budget-create",
                }, json={"title": "行程", "snapshot": {"stops": []}})
                assert created.status_code == 201, created.text
                session_id = created.json()["id"]
                upgraded = await client.post(f"/api/tour-sessions/{session_id}/upgrade-v2", headers={
                    **write_headers, "Idempotency-Key": "budget-upgrade",
                }, json={"expected_version": 1})
                assert upgraded.status_code == 200, upgraded.text
                stop_id = str(uuid4())
                saved = await client.put(f"/api/tour-sessions/{session_id}/v2", headers={
                    **write_headers, "Idempotency-Key": "budget-save",
                }, json={
                    "expected_version": 2,
                    "snapshot": {
                        "schema_version": 2,
                        "constraints": {"available_minutes": 60},
                        "stops": [{"stop_id": stop_id, "kind": "rest", "name": "休息点",
                            "duration_minutes": 20, "duration_basis": "user"}],
                        "legs": [],
                    },
                })
                assert saved.status_code == 200, saved.text
                started = await client.post(f"/api/tour-sessions/{session_id}/start", headers={
                    **write_headers, "Idempotency-Key": "budget-start",
                }, json={"expected_version": 3})
                assert started.status_code == 200, started.text

                conservative = await client.get(f"/api/tour-sessions/{session_id}/budget")
                explicit = await client.get(
                    f"/api/tour-sessions/{session_id}/budget?current_stop_remaining_minutes=5")
                invalid = await client.get(
                    f"/api/tour-sessions/{session_id}/budget?current_stop_remaining_minutes=-1")

                assert conservative.status_code == 200, conservative.text
                assert conservative.json()["known_minutes"] == 20
                assert conservative.json()["estimated_current_stop"] is True
                assert explicit.status_code == 200, explicit.text
                assert explicit.json()["known_minutes"] == 5
                assert explicit.json()["estimated_current_stop"] is False
                assert invalid.status_code == 422
        finally:
            await engine.dispose()

    asyncio.run(scenario())
