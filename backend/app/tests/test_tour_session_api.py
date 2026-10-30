from __future__ import annotations

import asyncio

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import tour_sessions
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.api.auth import create_admin_token
from app.tests.async_db import open_test_session


def test_tour_session_api_scopes_access_and_preserves_conflicts():
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
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://testserver") as owner:
                bootstrap = await owner.get("/api/tour-sessions/bootstrap")
                assert bootstrap.status_code == 200
                csrf = bootstrap.json()["csrf_token"]
                headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf, "Idempotency-Key": "create-1"}
                created = await owner.post("/api/tour-sessions", headers=headers, json={
                    "title": "亲子游", "snapshot": {"constraints": {"available_minutes": 180}, "stops": []},
                })
                assert created.status_code == 201
                task = created.json()
                assert task["site_id"] == "lingshan"
                assert task["version"] == 1
                artifact = await owner.post(f"/api/tour-sessions/{task['id']}/artifacts", headers={
                    "Origin": "http://testserver", "X-CSRF-Token": csrf,
                }, json={"artifact_type": "itinerary", "artifact_id": "itinerary-v1", "revision_id": task["revision_id"]})
                assert artifact.status_code == 201
                assert len((await owner.get(f"/api/tour-sessions/{task['id']}/artifacts")).json()["items"]) == 1
                replay = await owner.post("/api/tour-sessions", headers=headers, json={
                    "title": "亲子游", "snapshot": {"constraints": {"available_minutes": 180}, "stops": []},
                })
                assert replay.status_code == 201, replay.text
                assert replay.json()["id"] == task["id"]
                changed_duplicate = await owner.post("/api/tour-sessions", headers=headers, json={
                    "title": "改了内容", "snapshot": {"constraints": {"available_minutes": 180}, "stops": []},
                })
                assert changed_duplicate.status_code == 409
                missing_csrf = await owner.post("/api/tour-sessions", headers={
                    "Origin": "http://testserver", "Idempotency-Key": "create-2",
                }, json={"title": "没有 csrf"})
                assert missing_csrf.status_code == 403

                async with AsyncClient(transport=transport, base_url="http://testserver") as stranger:
                    stranger_bootstrap = await stranger.get("/api/tour-sessions/bootstrap")
                    stranger_csrf = stranger_bootstrap.json()["csrf_token"]
                    admin_token = create_admin_token("tour-session-test-secret")
                    assert (await stranger.get(f"/api/tour-sessions/{task['id']}", headers={
                        "Authorization": f"Bearer {admin_token}",
                    })).status_code == 404
                    assert (await stranger.get(f"/api/tour-sessions/{task['id']}/events")).status_code == 404
                    denied = await stranger.put(f"/api/tour-sessions/{task['id']}", headers={
                        "Origin": "http://testserver", "X-CSRF-Token": stranger_csrf, "Idempotency-Key": "save-1",
                    }, json={"expected_version": 1, "snapshot": {"stops": [{"name": "灵山大佛"}]}})
                    assert denied.status_code == 404

                save_headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf, "Idempotency-Key": "save-1"}
                saved = await owner.put(f"/api/tour-sessions/{task['id']}", headers=save_headers, json={
                    "expected_version": 1, "snapshot": {"stops": [{"name": "灵山大佛"}]},
                })
                assert saved.status_code == 200
                stale = await owner.put(f"/api/tour-sessions/{task['id']}", headers={
                    **save_headers, "Idempotency-Key": "save-2",
                }, json={"expected_version": 1, "snapshot": {"stops": [{"name": "佛足坛"}]}})
                assert stale.status_code == 409
                assert stale.json()["detail"]["current_version"] == 2

                deleted = await owner.delete(f"/api/tour-sessions/{task['id']}?expected_version=2", headers={
                    "Origin": "http://testserver", "X-CSRF-Token": csrf,
                })
                assert deleted.status_code == 200
                assert len((await owner.get("/api/tour-sessions/trash")).json()["items"]) == 1
                recovered = await owner.post(f"/api/tour-sessions/{task['id']}/undelete", headers={
                    "Origin": "http://testserver", "X-CSRF-Token": csrf,
                })
                assert recovered.status_code == 200
                assert recovered.json()["snapshot"]["stops"][0]["name"] == "灵山大佛"
                events = (await owner.get(f"/api/tour-sessions/{task['id']}/events")).json()["items"]
                assert [event["event_type"] for event in events] == [
                    "created", "artifact_linked", "saved", "deleted", "recovered",
                ]
                purge_without_confirmation = await owner.delete(
                    f"/api/tour-sessions/{task['id']}/purge", headers={
                        "Origin": "http://testserver", "X-CSRF-Token": csrf,
                    },
                )
                assert purge_without_confirmation.status_code == 400

                bootstrap_again = await owner.get("/api/tour-sessions/bootstrap")
                assert bootstrap_again.json()["csrf_token"]
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_v2_upgrade_start_progress_and_legacy_downgrade_protection():
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
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                csrf = (await client.get("/api/tour-sessions/bootstrap")).json()["csrf_token"]
                write_headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}
                created = await client.post("/api/tour-sessions", headers={**write_headers, "Idempotency-Key": "create-v2"}, json={
                    "title": "行程", "snapshot": {"stops": [{"name": "未发布地点"}]},
                })
                assert created.status_code == 201, created.text
                session_id = created.json()["id"]
                legacy_proposal = await client.post(f"/api/tour-sessions/{session_id}/proposals", headers={
                    **write_headers, "Idempotency-Key": "legacy-proposal",
                }, json={"expected_version": 1, "progress_version": 0, "draft_digest": "0" * 64,
                    "draft_snapshot": {"schema_version": 2, "stops": []}, "text": "增加一个景点"})
                assert legacy_proposal.status_code == 409, legacy_proposal.text
                upgraded = await client.post(f"/api/tour-sessions/{session_id}/upgrade-v2", headers={
                    **write_headers, "Idempotency-Key": "upgrade-v2",
                }, json={"expected_version": 1})
                assert upgraded.status_code == 200, upgraded.text
                assert upgraded.json()["snapshot"]["schema_version"] == 2
                started = await client.post(f"/api/tour-sessions/{session_id}/start", headers={
                    **write_headers, "Idempotency-Key": "start-v2",
                }, json={"expected_version": 2})
                assert started.status_code == 200, started.text
                stop_id = next(iter(started.json()["status_by_stop"]))
                completed = await client.post(f"/api/tour-sessions/{session_id}/progress", headers={
                    **write_headers, "Idempotency-Key": "complete-v2",
                }, json={"expected_progress_version": 1, "command": {"type": "complete", "stop_id": stop_id}})
                assert completed.status_code == 200, completed.text
                assert completed.json()["status"] == "finished"
                events = (await client.get(f"/api/tour-sessions/{session_id}/progress/events")).json()["items"]
                assert [item["event_type"] for item in events] == ["started", "completed"]
                downgrade = await client.put(f"/api/tour-sessions/{session_id}", headers={
                    **write_headers, "Idempotency-Key": "legacy-downgrade",
                }, json={"expected_version": 2, "snapshot": {"stops": []}})
                assert downgrade.status_code == 409
        finally:
            await engine.dispose()
    asyncio.run(scenario())
