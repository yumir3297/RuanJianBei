from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import tour_sessions
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.tour_session import TourIdentity
from app.repositories.tour_session import TourSessionRepository
from app.schemas.itinerary import TourSnapshotV2
from app.services.itinerary.catalog import PublishedAttraction, build_catalog_snapshot
from app.services.itinerary.intent import snapshot_digest
from app.services.tool_execution import handlers
from app.services.tool_execution.runner import ToolRunner
from app.tests.async_db import open_test_session


@pytest.mark.parametrize("withdraw_catalog", [True, False])
def test_worker_proposal_apply_with_catalog_change_or_stable_catalog(monkeypatch, withdraw_catalog):
    async def scenario():
        engine, db = await open_test_session()
        owner = TourIdentity(id="owner-a", credential_digest="a" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1))
        db.add(owner)
        await db.commit()
        snapshot = TourSnapshotV2.model_validate({
            "schema_version": 2,
            "constraints": {"available_minutes": 90},
            "stops": [{"kind": "rest", "name": "休息点", "duration_minutes": 10,
                "duration_basis": "user"}],
        })
        repo = TourSessionRepository(db)
        created = await repo.create_session(owner.id, "lingshan", "游览", snapshot.model_dump(mode="json"), "create")
        started = await repo.start_progress(owner.id, created["id"], created["version"], "start")
        await db.close()

        sessions = async_sessionmaker(bind=engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(tour_sessions.router, prefix="/api/tour-sessions")

        async def db_dependency():
            async with sessions() as session:
                yield session

        app.dependency_overrides[get_db_session] = db_dependency
        app.dependency_overrides[get_app_settings] = lambda: Settings(
            site_id="lingshan", admin_token_secret="test-secret",
        )
        app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
        monkeypatch.setattr(tour_sessions, "_protect_write", lambda *_args: None)
        published_rows = {"items": [PublishedAttraction(
            site_id="lingshan", spot_code="LS-01", entry_id="entry-1",
            published_revision_id="revision-1", title="梵宫",
        )]}

        async def fake_catalog(_catalog, site_id):
            return build_catalog_snapshot(site_id, published_rows["items"])

        async def fake_propose(_service, _text, draft, _catalog, _settings):
            candidate = draft.model_copy(deep=True)
            candidate.stops[0].duration_minutes = 15
            return {
                "status": "ready",
                "operations": [{"type": "set_duration", "stop_id": str(candidate.stops[0].stop_id), "duration_minutes": 15}],
                "candidate": candidate.model_dump(mode="json"),
                "diff": [{"kind": "changed"}],
                "validation": {"status": "pass", "conflicts": []},
                "clarification": None,
            }

        monkeypatch.setattr(tour_sessions.PublishedAttractionCatalog, "list_for_site", fake_catalog)
        monkeypatch.setattr(handlers.ItineraryIntentService, "propose", fake_propose)
        monkeypatch.setattr(handlers, "AsyncSessionLocal", sessions)
        monkeypatch.setattr(handlers, "get_settings", lambda: Settings(
            llm_provider="test", llm_api_key="fake", llm_base_url="https://unused.invalid", llm_model="fake",
        ))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                headers = {"Idempotency-Key": "proposal", "Origin": "http://testserver"}
                payload_snapshot = snapshot.model_dump(mode="json")
                digest = snapshot_digest(snapshot)
                proposal_response = await client.post(
                    f"/api/tour-sessions/{created['id']}/proposals", headers=headers, json={
                        "expected_version": created["version"],
                        "progress_version": started["progress_version"],
                        "draft_digest": digest,
                        "draft_snapshot": payload_snapshot,
                        "text": "休息 15 分钟",
                    },
                )
                assert proposal_response.status_code == 202, proposal_response.text
                queued = proposal_response.json()
                assert queued["status"] == "executing" and queued["execution_job_id"]
                assert await ToolRunner(sessions, handlers.build_registry()).run_one("catalog-worker")
                recovered = await client.get(
                    f"/api/tour-sessions/{created['id']}/proposals/{queued['id']}"
                )
                assert recovered.status_code == 200
                proposal = recovered.json()
                assert proposal["status"] == "ready"
                initial_catalog_digest = proposal["catalog_digest"]

                if not withdraw_catalog:
                    apply_path = f"/api/tour-sessions/{created['id']}/proposals/{proposal['id']}/apply"
                    apply_headers = {"Idempotency-Key": "apply", "Origin": "http://testserver"}
                    apply_payload = {"expected_version": created["version"],
                                     "progress_version": started["progress_version"], "draft_digest": digest}
                    applied = await client.post(apply_path, headers=apply_headers, json=apply_payload)
                    published_rows["items"] = []  # Catalog changes after the successful commit.
                    replay = await client.post(apply_path, headers=apply_headers, json=apply_payload)
                    assert applied.status_code == 200, applied.text
                    assert replay.status_code == 200, replay.text
                    assert replay.json() == applied.json()
                    changed = await client.post(apply_path, headers=apply_headers,
                                                json={**apply_payload, "expected_version": created["version"] + 1})
                    assert changed.status_code == 409
                    assert applied.json()["version"] == created["version"] + 1
                    assert applied.json()["snapshot"]["stops"][0]["duration_minutes"] == 15
                    async with sessions() as check_db:
                        check_repo = TourSessionRepository(check_db)
                        revisions = await check_repo.list_revisions(owner.id, created["id"])
                        progress = await check_repo.get_progress(owner.id, created["id"])
                    assert len(revisions) == 2
                    assert progress["progress_version"] == started["progress_version"] + 1
                    assert progress["status_by_stop"] == started["status_by_stop"]
                    return

                # A published entry is withdrawn; the catalog digest is derived from
                # the actual remaining published rows rather than hand-edited.
                published_rows["items"] = []
                withdrawn_catalog = build_catalog_snapshot("lingshan", published_rows["items"])
                assert withdrawn_catalog.digest != initial_catalog_digest

                async with sessions() as before_db:
                    before_repo = TourSessionRepository(before_db)
                    before_tour = await before_repo.get_session(owner.id, created["id"])
                    before_revisions = await before_repo.list_revisions(owner.id, created["id"])
                    before_tour_events = await before_repo.list_events(owner.id, created["id"])
                    before_progress = await before_repo.get_progress(owner.id, created["id"])
                    before_progress_events = await before_repo.list_progress_events(owner.id, created["id"])
                apply_response = await client.post(
                    f"/api/tour-sessions/{created['id']}/proposals/{proposal['id']}/apply",
                    headers={"Idempotency-Key": "apply", "Origin": "http://testserver"},
                    json={
                        "expected_version": created["version"],
                        "progress_version": started["progress_version"],
                        "draft_digest": digest,
                    },
                )
                assert apply_response.status_code == 409, apply_response.text
                assert "景点资料已更新" in apply_response.text

                async with sessions() as check_db:
                    check_repo = TourSessionRepository(check_db)
                    current = await check_repo.get_session(owner.id, created["id"])
                    progress = await check_repo.get_progress(owner.id, created["id"])
                    revisions = await check_repo.list_revisions(owner.id, created["id"])
                    tour_events = await check_repo.list_events(owner.id, created["id"])
                    progress_events = await check_repo.list_progress_events(owner.id, created["id"])
                assert current["version"] == created["version"]
                assert current["snapshot"] == before_tour["snapshot"]
                assert [item["id"] for item in revisions] == [item["id"] for item in before_revisions]
                assert tour_events == before_tour_events
                assert progress["progress_version"] == started["progress_version"]
                assert progress == before_progress
                assert progress_events == before_progress_events
        finally:
            await engine.dispose()

    asyncio.run(scenario())
