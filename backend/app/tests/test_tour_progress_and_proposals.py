from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from app.tests.async_db import open_test_session


def _run(coro):
    asyncio.run(coro())


async def _seed_published_catalog(db):
    from app.models.knowledge import KnowledgeEntry
    from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
    from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog

    db.add(KnowledgeState(id=1, epoch=1))
    for code, title in [("LS-01", "梵宫"), ("LS-02", "其他景点"), ("LS-03", "新景点")]:
        metadata = json.dumps({"attraction_id": code})
        entry = KnowledgeEntry(title=title, category="景点信息", content="测试资料", source="测试", aliases="", metadata_json=metadata)
        db.add(entry)
        await db.flush()
        revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=title,
                                     category=entry.category, content=entry.content, source=entry.source,
                                     aliases="", metadata_json=metadata)
        db.add(revision)
        await db.flush()
        entry.published_revision_id = revision.id
    await db.commit()
    return (await PublishedAttractionCatalog(K01PublishedAttractionSource(db, site_id="site")).list_for_site("site")).digest


def _snapshot():
    stop_id = str(uuid4())
    return {"schema_version": 2, "constraints": {"available_minutes": 90},
        "stops": [{"stop_id": stop_id, "kind": "visit", "spot_code": "LS-01", "name": "梵宫",
                   "duration_minutes": 20, "duration_basis": "user"}],
        "legs": [], "source": "manual", "source_references": []}


def test_progress_is_persisted_with_independent_version_and_owner_scope():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        from app.services.itinerary.progress import ProgressCommand
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "site", "游览", _snapshot(), "create")
            started = await repo.start_progress("owner-a", created["id"], 1, "start")
            stop_id = next(iter(started["status_by_stop"]))
            assert started["progress_version"] == 1 and started["status"] == "active"
            done = await repo.command_progress("owner-a", created["id"], 1,
                ProgressCommand(type="complete", stop_id=stop_id), "complete")
            assert done["status"] == "finished" and done["progress_version"] == 2
            assert await repo.get_progress("owner-b", created["id"]) is None
            events = await repo.list_progress_events("owner-a", created["id"])
            assert [event["event_type"] for event in events] == ["started", "completed"]
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_confirm_remaining_budget_is_versioned_audited_and_idempotent():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        from app.services.itinerary.progress import ProgressCommand, ProgressConflict
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "site", "游览", _snapshot(), "create")
            now = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
            started = await repo.start_progress("owner-a", created["id"], 1, "start", now=now)
            command = ProgressCommand(type="set_remaining_budget", remaining_minutes=45)
            updated = await repo.command_progress("owner-a", created["id"], 1, command, "budget",
                now=now + timedelta(minutes=30))
            replay = await repo.command_progress("owner-a", created["id"], 1, command, "budget",
                now=now + timedelta(minutes=35))
            assert updated == replay
            assert datetime.fromisoformat(updated["finish_by"]) == now + timedelta(minutes=75)
            assert updated["progress_version"] == 2
            assert updated["status_by_stop"] == started["status_by_stop"]
            events = await repo.list_progress_events("owner-a", created["id"])
            assert events[-1]["event_type"] == "remaining_budget_set"
            assert events[-1]["payload"]["old_finish_by"] == started["finish_by"]
            assert events[-1]["payload"]["new_finish_by"] == updated["finish_by"]
            with pytest.raises(ProgressConflict):
                await repo.command_progress("owner-a", created["id"], 1, command, "stale", now=now)
            assert len(await repo.list_progress_events("owner-a", created["id"])) == 2
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_proposal_apply_creates_exactly_one_revision_and_is_idempotent():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            candidate = json.loads(json.dumps(snapshot))
            candidate["constraints"]["available_minutes"] = 60
            generated = {"status": "ready", "operations": [{"type": "update_constraints"}],
                "candidate": candidate, "diff": [{"kind": "constraints"}],
                "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                catalog_digest, "shorten the trip", generated, "proposal-create")
            assert (await repo.get_proposal("owner-b", created["id"], proposal["id"])) is None
            applied = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                "a" * 64, "proposal-apply", catalog_site_id="site")
            replay = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                "a" * 64, "proposal-apply", catalog_site_id="site")
            assert applied == replay and applied["version"] == 2
            assert applied["snapshot"]["constraints"]["available_minutes"] == 60
            assert len(await repo.list_revisions("owner-a", created["id"])) == 2
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_restored_proposal_diff_is_rebuilt_from_recorded_snapshots():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            candidate = json.loads(json.dumps(snapshot))
            candidate["stops"][0]["name"] = "已发布名称"
            candidate["stops"][0]["duration_minutes"] = 35
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [],
                "candidate": candidate, "diff": [{"kind": "changed", "after": {"name": "错误名称"}}],
                "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                catalog_digest, "修改", generated, "proposal")
            restored = await repo.get_proposal("owner-a", created["id"], proposal["id"])
            assert restored["diff"][0]["after"]["name"] == "已发布名称"
            assert restored["validation"]["status"] == "unverified"
            from app.models.tour_session import ItineraryProposal
            await db.execute(update(ItineraryProposal).where(ItineraryProposal.id == proposal["id"]).values(base_snapshot_json="{}"))
            await db.commit()
            restored = await repo.get_proposal("owner-a", created["id"], proposal["id"])
            assert restored["diff_verifiable"] is False
            with pytest.raises(ValueError, match="原始行程"):
                await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                          "a" * 64, "apply", catalog_site_id="site")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


@pytest.mark.parametrize("new_minutes", [20, 40])
def test_restored_old_proposal_does_not_present_replaced_spot_evidence(new_minutes):
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            first = snapshot["stops"][0]
            first.update(duration_basis="source", evidence=[{"evidence_type": "published_content", "reference_id": "old-spot"}])
            second_id = str(uuid4())
            snapshot["stops"].append({"stop_id": second_id, "kind": "visit", "spot_code": "LS-02", "name": "其他景点", "duration_minutes": 20, "duration_basis": "user"})
            snapshot["legs"] = [{"from_stop_id": first["stop_id"], "to_stop_id": second_id,
                "duration_minutes": 10, "duration_basis": "source", "evidence": [{"evidence_type": "published_content", "reference_id": "old-route"}]}]
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            candidate = json.loads(json.dumps(snapshot))
            candidate["stops"][0].update(spot_code="LS-03", name="新景点", duration_minutes=new_minutes)
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [], "candidate": candidate,
                "diff": [], "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64, catalog_digest, "替换", generated, "proposal")
            restored = await repo.get_proposal("owner-a", created["id"], proposal["id"])
            stop = restored["candidate"]["stops"][0]
            leg = restored["candidate"]["legs"][0]
            assert all(e.get("reference_id") != "old-spot" for e in stop["evidence"])
            assert all(e.get("reference_id") != "old-route" for e in leg["evidence"])
            assert restored["validation"]["status"] == "unverified"
            applied = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                                "a" * 64, "apply", catalog_site_id="site")
            applied_stop = applied["snapshot"]["stops"][0]
            applied_leg = applied["snapshot"]["legs"][0]
            assert applied_stop["duration_basis"] == stop["duration_basis"]
            assert applied_stop["evidence"] == stop["evidence"]
            assert applied_leg["duration_minutes"] == leg["duration_minutes"]
            assert applied_leg["evidence"] == leg["evidence"]
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_apply_proposal_preserves_manual_duration_from_unsaved_base_draft():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            draft = json.loads(json.dumps(snapshot))
            draft["stops"][0]["duration_minutes"] = 40
            draft["stops"][0]["evidence"] = [{"evidence_type": "visitor_input", "label": "游客填写的停留时长"}]
            candidate = json.loads(json.dumps(draft))
            candidate["constraints"]["available_minutes"] = 60
            candidate["stops"].append({"stop_id": str(uuid4()), "kind": "rest", "name": "休息",
                                       "duration_minutes": 10, "duration_basis": "user"})
            generated = {"status": "ready", "base_snapshot": draft, "operations": [], "candidate": candidate,
                         "diff": [], "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                catalog_digest, "调整时间预算", generated, "proposal")
            applied = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                                "a" * 64, "apply", catalog_site_id="site")
            stop = applied["snapshot"]["stops"][0]
            assert stop["duration_minutes"] == 40
            assert stop["duration_basis"] == "user"
            assert stop["evidence"][0]["evidence_type"] == "visitor_input"
            added = applied["snapshot"]["stops"][1]
            assert added["duration_basis"] == "estimate"
            assert added["evidence"][0]["evidence_type"] == "estimate"
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_legacy_proposal_cannot_add_an_unpublished_free_text_visit():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            candidate = json.loads(json.dumps(snapshot))
            candidate["stops"].append({"stop_id": str(uuid4()), "kind": "visit", "name": "未核实景点"})
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [], "candidate": candidate,
                         "diff": [], "validation": {"status": "unverified", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                catalog_digest, "添加景点", generated, "proposal")
            with pytest.raises(ValueError, match="已发布"):
                await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                          "a" * 64, "apply", catalog_entries={}, catalog_site_id="site")
            assert (await repo.get_session("owner-a", created["id"]))["version"] == 1
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_proposal_keeps_unchanged_manually_entered_visit():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            snapshot["stops"][0]["spot_code"] = None
            snapshot["stops"][0]["name"] = "游客自填地点"
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            candidate = json.loads(json.dumps(snapshot))
            candidate["constraints"]["available_minutes"] = 60
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [], "candidate": candidate,
                         "diff": [], "validation": {"status": "unverified", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                catalog_digest, "调整预算", generated, "proposal")
            applied = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                                "a" * 64, "apply", catalog_entries={}, catalog_site_id="site")
            assert applied["snapshot"]["stops"][0]["name"] == "游客自填地点"
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_active_proposal_apply_refreshes_progress_version_for_next_command():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        from app.services.itinerary.progress import ProgressCommand
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            started = await repo.start_progress("owner-a", created["id"], 1, "start")
            stop_id = next(iter(started["status_by_stop"]))

            candidate = json.loads(json.dumps(snapshot))
            candidate["constraints"]["interests"] = ["历史"]
            generated = {"status": "ready", "operations": [{"type": "update_constraints"}],
                "candidate": candidate, "diff": [{"kind": "constraints"}],
                "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1,
                started["progress_version"], "c" * 64, catalog_digest, "缩短总时长",
                generated, "active-proposal-create")

            applied = await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1,
                started["progress_version"], "c" * 64, "active-proposal-apply", catalog_site_id="site")
            reconciled = await repo.get_progress("owner-a", created["id"])
            assert applied["version"] == 2
            assert reconciled["progress_version"] == started["progress_version"] + 1

            finished = await repo.command_progress("owner-a", created["id"],
                reconciled["progress_version"], ProgressCommand(type="complete", stop_id=stop_id),
                "complete-after-proposal")
            assert finished["status"] == "finished"
            assert finished["progress_version"] == reconciled["progress_version"] + 1
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


@pytest.mark.parametrize("via_proposal", [False, True])
def test_active_tour_rejects_total_budget_change_without_rewriting_deadline(via_proposal):
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            started = await repo.start_progress("owner-a", created["id"], 1, "start")
            candidate = json.loads(json.dumps(snapshot))
            candidate["constraints"]["available_minutes"] = 60
            if via_proposal:
                generated = {"status": "ready", "operations": [], "candidate": candidate,
                    "diff": [], "validation": {"status": "pass", "conflicts": []}}
                proposal = await repo.create_proposal("owner-a", created["id"], 1,
                    started["progress_version"], "d" * 64, catalog_digest, "缩短时长", generated, "proposal")
                change = repo.apply_proposal("owner-a", created["id"], proposal["id"], 1,
                    started["progress_version"], "d" * 64, "apply", catalog_site_id="site")
            else:
                change = repo.save_revision("owner-a", created["id"], 1, candidate, "save")
            with pytest.raises(ValueError, match="进行中.*总时长"):
                await change
            assert (await repo.get_session("owner-a", created["id"]))["version"] == 1
            current = await repo.get_progress("owner-a", created["id"])
            assert current["finish_by"] == started["finish_by"]
            assert current["progress_version"] == started["progress_version"]
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_proposal_reservation_prevents_duplicate_provider_execution_and_replays_result():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository, IdempotencyConflict
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            digest = "b" * 64
            reservation, owns = await repo.reserve_proposal("owner-a", created["id"], 1, 0,
                digest, "catalog", "增加休息", snapshot, "proposal-key")
            replay, replay_owns = await repo.reserve_proposal("owner-a", created["id"], 1, 0,
                digest, "catalog", "增加休息", snapshot, "proposal-key")
            assert owns and not replay_owns
            assert replay["id"] == reservation["id"] and replay["status"] == "executing"
            generated = {"status": "ready", "operations": [{"type": "add_rest"}],
                "candidate": snapshot, "diff": [], "validation": {"status": "unverified", "conflicts": []}}
            completed = await repo.complete_reserved_proposal("owner-a", created["id"], reservation["id"],
                generated, "proposal-key")
            replay, replay_owns = await repo.reserve_proposal("owner-a", created["id"], 1, 0,
                digest, "catalog", "增加休息", snapshot, "proposal-key")
            assert completed["status"] == "ready" and replay == completed and not replay_owns
            try:
                await repo.reserve_proposal("owner-a", created["id"], 1, 0,
                    digest, "catalog", "改为别的请求", snapshot, "proposal-key")
            except IdempotencyConflict:
                pass
            else:
                raise AssertionError("same key with different request must conflict")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_legacy_save_cannot_downgrade_v2_snapshot():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            created = await repo.create_session("owner-a", "site", "游览", _snapshot(), "create")
            try:
                await repo.save_revision("owner-a", created["id"], 1, {"stops": []}, "legacy-save")
            except ValueError as error:
                assert "V2" in str(error)
            else:
                raise AssertionError("legacy save must not erase a V2 itinerary")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_v2_save_cannot_bypass_a_stop_duration_lock():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            snapshot["stops"][0]["locked_fields"] = ["duration"]
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            changed = json.loads(json.dumps(snapshot))
            changed["stops"][0]["duration_minutes"] = 35
            try:
                await repo.save_revision("owner-a", created["id"], 1, changed, "change-locked-duration")
            except ValueError as error:
                assert "locked" in str(error) or "锁定" in str(error)
            else:
                raise AssertionError("V2 save must enforce server-side stop locks")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_v2_save_reconstructs_untrusted_provenance_instead_of_trusting_client_fields():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            forged = json.loads(json.dumps(snapshot))
            forged["stops"][0]["created_by"] = "ai"
            forged["stops"][0]["duration_minutes"] = 25
            forged["stops"][0]["duration_basis"] = "estimate"
            forged["stops"][0]["evidence"] = [{"evidence_type": "published_content", "reference_id": "forged"}]
            forged["stops"].append({"stop_id": str(uuid4()), "kind": "rest", "name": "休息",
                "duration_minutes": 10, "duration_basis": "estimate", "created_by": "ai",
                "evidence": [{"evidence_type": "estimate", "label": "伪造"}]})
            saved = await repo.save_revision("owner-a", created["id"], 1, forged, "save-forged-provenance")
            original, added = saved["snapshot"]["stops"]
            assert original["created_by"] == "manual"
            assert original["duration_basis"] == "user"
            assert original["evidence"][0]["evidence_type"] == "visitor_input"
            assert added["created_by"] == "manual"
            assert added["duration_basis"] == "user"
            assert added["evidence"][0]["evidence_type"] == "visitor_input"
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_active_plan_revision_reconciles_new_pending_stops_and_fences_stale_progress():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        from app.services.itinerary.progress import ProgressCommand, ProgressConflict
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            started = await repo.start_progress("owner-a", created["id"], 1, "start")
            added_id = str(uuid4())
            candidate = json.loads(json.dumps(snapshot))
            candidate["stops"].append({"stop_id": added_id, "kind": "visit", "name": "新增景点",
                "duration_basis": "unknown"})
            saved = await repo.save_revision("owner-a", created["id"], 1, candidate, "save-v2")
            progress = await repo.get_progress("owner-a", created["id"])
            assert saved["version"] == 2
            assert progress["progress_version"] == started["progress_version"] + 1
            assert progress["status_by_stop"][added_id] == "pending"
            try:
                await repo.command_progress("owner-a", created["id"], started["progress_version"],
                    ProgressCommand(type="complete", stop_id=next(iter(started["status_by_stop"]))), "stale")
            except ProgressConflict:
                pass
            else:
                raise AssertionError("a plan reconciliation must fence stale progress commands")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_active_plan_revision_rejects_new_pending_stop_before_current_stop():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            snapshot["stops"].append({"stop_id": str(uuid4()), "kind": "rest", "name": "休息",
                "duration_minutes": 5, "duration_basis": "user"})
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            started = await repo.start_progress("owner-a", created["id"], 1, "start")
            current_id = started["current_stop_id"]
            candidate = json.loads(json.dumps(snapshot))
            inserted_id = str(uuid4())
            candidate["stops"].insert(0, {"stop_id": inserted_id, "kind": "rest", "name": "新增休息",
                "duration_minutes": 5, "duration_basis": "user"})
            try:
                await repo.save_revision("owner-a", created["id"], 1, candidate, "insert-before-current")
            except ValueError as error:
                assert "当前点之前" in str(error)
            else:
                raise AssertionError("a new pending stop must not be inserted before the current stop")
            assert current_id == next(stop for stop, state in started["status_by_stop"].items() if state == "current")
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_save_revision_status_fence_rejects_session_state_change_before_commit(monkeypatch):
    async def scenario():
        from app.models.tour_session import TourSession
        from app.repositories.tour_session import RevisionConflict, TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create")
            await repo.start_progress("owner-a", created["id"], 1, "start")
            original_reconcile = repo._reconcile_progress_for_plan_change

            async def change_status_before_revision(session_id, before, after, row):
                await original_reconcile(session_id, before, after, row)
                await db.execute(update(TourSession).where(TourSession.id == session_id).values(status="completed"))

            monkeypatch.setattr(repo, "_reconcile_progress_for_plan_change", change_status_before_revision)
            candidate = json.loads(json.dumps(snapshot))
            candidate["constraints"]["interests"] = ["自然"]
            try:
                await repo.save_revision("owner-a", created["id"], 1, candidate, "racing-save")
            except RevisionConflict as error:
                assert error.current_version == 1
            else:
                raise AssertionError("revision save must fail if the session status changed after its read")
            assert len(await repo.list_revisions("owner-a", created["id"])) == 1
            progress = await repo.get_progress("owner-a", created["id"])
            assert progress["progress_version"] == 1
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_restored_old_proposal_with_rest_interval_is_unverified():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            snapshot = _snapshot()
            snapshot["constraints"]["rest_every_minutes"] = 30
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create-rest")
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [],
                         "candidate": snapshot, "diff": [],
                         "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                                                  "catalog", "安排休息", generated, "proposal-rest")
            restored = await repo.get_proposal("owner-a", created["id"], proposal["id"])
            assert restored["validation"]["status"] == "unverified"
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


@pytest.mark.parametrize("validation_status", ["conflict", "unexpected"])
def test_apply_rejects_conflicting_or_unknown_validation(validation_status):
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            snapshot = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", snapshot, "create-invalid")
            generated = {"status": "ready", "base_snapshot": snapshot, "operations": [],
                         "candidate": snapshot, "diff": [],
                         "validation": {"status": validation_status, "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                                                  catalog_digest, "调整", generated, "proposal-invalid")
            with pytest.raises(ValueError, match="校验"):
                await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                          "a" * 64, "apply-invalid", catalog_site_id="site")
            assert len(await repo.list_revisions("owner-a", created["id"])) == 1
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)


def test_old_pass_proposal_with_conflicting_constraints_is_rejected():
    async def scenario():
        from app.repositories.tour_session import TourSessionRepository
        engine, db = await open_test_session()
        try:
            repo = TourSessionRepository(db)
            catalog_digest = await _seed_published_catalog(db)
            base = _snapshot()
            created = await repo.create_session("owner-a", "site", "游览", base, "create-conflict")
            candidate = json.loads(json.dumps(base))
            candidate["constraints"]["excluded_spots"] = ["LS-01"]
            generated = {"status": "ready", "base_snapshot": base, "operations": [],
                         "candidate": candidate, "diff": [],
                         "validation": {"status": "pass", "conflicts": []}, "clarification": None}
            proposal = await repo.create_proposal("owner-a", created["id"], 1, 0, "a" * 64,
                                                  catalog_digest, "调整", generated, "old-conflict")
            restored = await repo.get_proposal("owner-a", created["id"], proposal["id"])
            assert restored["validation"]["status"] == "conflict"
            with pytest.raises(ValueError, match="校验"):
                await repo.apply_proposal("owner-a", created["id"], proposal["id"], 1, 0,
                                          "a" * 64, "apply-conflict", catalog_site_id="site")
            assert len(await repo.list_revisions("owner-a", created["id"])) == 1
        finally:
            await db.close(); await engine.dispose()
    _run(scenario)
