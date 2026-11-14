import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.api.auth import create_admin_token
from app.api.guide_loop import router
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.guide_loop import GuideLoopCase, GuideLoopCheck, GuideLoopPointer, GuideLoopRevision
from app.tests.async_db import open_test_session


def make_client(db_path):
    app = FastAPI()
    app.include_router(router, prefix="/api/admin/guide-loop")
    async def db():
        engine, session = await open_test_session(str(db_path))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()
    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_app_settings] = lambda: Settings(app_env="test", guide_loop_pilot_enabled=True, admin_token_secret="test-guide-loop-secret-key")
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_admin_token("test-guide-loop-secret-key")
    return client


def test_publish_requires_server_verified_draft_and_moves_revision(tmp_path):
    db_path = tmp_path / "publication.db"
    client = make_client(db_path)
    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add(GuideLoopCase(cluster_id="case-1", category="retrieval_gap", status="open"))
            await session.commit()
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(seed())
    draft = client.post("/api/admin/guide-loop/cases/case-1/draft", json={
        "base_revision":"0", "action":"add_alias", "poi_id":"bathing", "target_id":"prince",
        "alias":"花里面的小孩", "answer":"这是莲花里的太子佛。", "evidence":{"evidence_id":"gazetteer-1","source_ref":"Wuxi gazetteer"},
        "effective_from":"2026-11-10T00:00:00+08:00", "effective_until":None,
    })
    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]
    unverified = client.post("/api/admin/guide-loop/cases/case-1/publish", json={"draft_id":draft_id,"base_revision":"0"})
    assert unverified.status_code == 409
    verified = client.post("/api/admin/guide-loop/cases/case-1/verify", json={"draft_id":draft_id})
    assert verified.status_code == 200 and verified.json()["passed"] is True
    assert verified.json()["verification_type"] == "deterministic_route_and_structure"
    assert verified.json()["fact_checked"] is False
    assert verified.json()["human_source_review_required"] is True
    unreviewed = client.post("/api/admin/guide-loop/cases/case-1/publish", json={"draft_id":draft_id,"base_revision":"0"})
    assert unreviewed.status_code == 409
    published = client.post("/api/admin/guide-loop/cases/case-1/publish", json={"draft_id":draft_id,"base_revision":"0","source_reviewed":True})
    assert published.status_code == 200
    assert published.json()["status"] == "published_pending_check"
    assert published.json()["source_reviewed"] is True
    assert published.json()["source_reviewed_at"]
    async def review_recorded():
        engine, session = await open_test_session(str(db_path))
        try:
            revision = await session.get(GuideLoopRevision, published.json()["revision_id"])
            assert revision.source_reviewed is True
            assert revision.source_reviewed_at is not None
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(review_recorded())
    repeated = client.post("/api/admin/guide-loop/cases/case-1/publish", json={"draft_id":draft_id,"base_revision":"0","source_reviewed":True})
    assert repeated.status_code == 200
    assert repeated.json()["revision_id"] == published.json()["revision_id"]


def test_publish_adds_alias_without_dropping_existing_aliases(tmp_path):
    db_path = tmp_path / "alias-history.db"
    client = make_client(db_path)

    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="case-alias", category="retrieval_gap", status="open"),
                GuideLoopRevision(revision_id="gl-base", base_revision="0", case_id="case-alias", poi_id="bathing", target_id="prince", action="add_alias", alias="莲花里的太子佛|莲花里是谁", answer="莲花里有太子佛立像。", evidence_id="e1", source_ref="公开方志", effective_from=now, status="published", created_at=now),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-base"),
            ])
            await session.commit()
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(seed())
    draft = client.post("/api/admin/guide-loop/cases/case-alias/draft", json={
        "base_revision":"gl-base", "action":"add_alias", "poi_id":"bathing", "target_id":"prince",
        "alias":"花台里的小孩", "answer":"莲花里有太子佛立像。", "evidence":{"evidence_id":"gazetteer-2","source_ref":"Wuxi gazetteer"},
        "effective_from":"2026-11-10T00:00:00+08:00", "effective_until":None,
    })
    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]
    assert client.post("/api/admin/guide-loop/cases/case-alias/verify", json={"draft_id":draft_id}).json()["passed"]
    published = client.post("/api/admin/guide-loop/cases/case-alias/publish", json={"draft_id":draft_id,"base_revision":"gl-base","source_reviewed":True})
    assert published.status_code == 200

    async def check_aliases():
        engine, session = await open_test_session(str(db_path))
        try:
            revision = await session.get(GuideLoopRevision, published.json()["revision_id"])
            assert revision.alias == "莲花里的太子佛|莲花里是谁|花台里的小孩"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(check_aliases())


def test_replace_fact_without_new_alias_reuses_existing_route_aliases(tmp_path):
    db_path = tmp_path / "replace-fact-alias.db"
    client = make_client(db_path)
    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="case-fact", category="stale_or_conflict", status="open"),
                GuideLoopRevision(revision_id="gl-fact-base", base_revision="0", case_id="case-fact", poi_id="bathing", target_id="prince", action="add_alias", alias="莲花里是谁|莲花中的佛像", answer="旧答案", evidence_id="e1", source_ref="旧方志", effective_from=now, status="published", created_at=now),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-fact-base"),
            ])
            await session.commit()
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(seed())
    draft = client.post("/api/admin/guide-loop/cases/case-fact/draft", json={
        "base_revision":"gl-fact-base", "action":"replace_fact", "poi_id":"bathing", "target_id":"prince",
        "answer":"经复核后的新答案。", "evidence":{"evidence_id":"e2","source_ref":"新方志"},
        "effective_from":"2026-11-10T00:00:00+08:00",
    }).json()
    verified = client.post("/api/admin/guide-loop/cases/case-fact/verify", json={"draft_id":draft["draft_id"]})
    assert verified.status_code == 200 and verified.json()["passed"] is True
    published = client.post("/api/admin/guide-loop/cases/case-fact/publish", json={"draft_id":draft["draft_id"],"base_revision":"gl-fact-base","source_reviewed":True})
    assert published.status_code == 200
    async def check_revision():
        engine, session = await open_test_session(str(db_path))
        try:
            revision = await session.get(GuideLoopRevision, published.json()["revision_id"])
            assert revision.alias == "莲花里是谁|莲花中的佛像"
            assert revision.answer == "经复核后的新答案。"
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(check_revision())


def test_stale_base_revision_is_conflict_and_does_not_publish(tmp_path):
    db_path = tmp_path / "stale-base-revision.db"
    client = make_client(db_path)

    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add(GuideLoopCase(cluster_id="stale", category="retrieval_gap", status="open"))
            await session.commit()
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(seed())
    draft = client.post("/api/admin/guide-loop/cases/stale/draft", json={
        "base_revision":"0", "action":"add_alias", "poi_id":"bathing", "target_id":"prince",
        "alias":"新莲花问法", "answer":"这是已编辑答案。", "evidence":{"evidence_id":"e1","source_ref":"公开方志"},
        "effective_from":"2026-11-10T00:00:00+08:00",
    }).json()
    assert client.post("/api/admin/guide-loop/cases/stale/verify", json={"draft_id":draft["draft_id"]}).json()["passed"]

    async def advance_pointer():
        engine, session = await open_test_session(str(db_path))
        try:
            pointer = await session.get(GuideLoopPointer, "bathing:prince")
            pointer.revision_id = "gl-newer"
            await session.commit()
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(advance_pointer())
    response = client.post("/api/admin/guide-loop/cases/stale/publish", json={"draft_id":draft["draft_id"],"base_revision":"0","source_reviewed":True})
    assert response.status_code == 409

    async def assert_not_published():
        engine, session = await open_test_session(str(db_path))
        try:
            pointer = await session.get(GuideLoopPointer, "bathing:prince")
            assert pointer.revision_id == "gl-newer"
            revisions = (await session.scalars(select(GuideLoopRevision).where(GuideLoopRevision.case_id == "commit-fail"))).all()
            assert revisions == []
            assert (await session.get(GuideLoopCase, "stale")).status == "verified"
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(assert_not_published())


def test_two_drafts_from_same_base_only_one_can_publish(tmp_path):
    db_path = tmp_path / "stale-base.db"
    client = make_client(db_path)
    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add_all([GuideLoopCase(cluster_id="case-a",category="retrieval_gap"),GuideLoopCase(cluster_id="case-b",category="retrieval_gap")])
            await session.commit()
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(seed())
    payload={"base_revision":"0","action":"add_alias","poi_id":"bathing","target_id":"prince","alias":"花台里的小孩","answer":"莲花里的太子佛立像。","evidence":{"evidence_id":"gazetteer-1","source_ref":"公开方志"},"effective_from":"2026-11-10T00:00:00+08:00"}
    drafts=[]
    for case_id in ("case-a","case-b"):
        draft=client.post(f"/api/admin/guide-loop/cases/{case_id}/draft",json=payload)
        assert draft.status_code==200
        drafts.append(draft.json()["draft_id"])
        assert client.post(f"/api/admin/guide-loop/cases/{case_id}/verify",json={"draft_id":drafts[-1]}).json()["passed"]
    publish_payloads = [
        ("case-a", drafts[0]),
        ("case-b", drafts[1]),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda item: client.post(f"/api/admin/guide-loop/cases/{item[0]}/publish", json={"draft_id":item[1],"base_revision":"0","source_reviewed":True}),
            publish_payloads,
        ))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner_id = next(response.json()["revision_id"] for response in responses if response.status_code == 200)
    winner_case = next(case for case, response in zip(("case-a", "case-b"), responses) if response.status_code == 200)
    retry=client.post(f"/api/admin/guide-loop/cases/{winner_case}/publish",json={"draft_id":drafts[0 if winner_case == "case-a" else 1],"base_revision":"0","source_reviewed":True})
    assert retry.json()["revision_id"]==winner_id


def test_stale_session_cannot_publish_over_a_newer_unverified_draft(tmp_path):
    from app.schemas.guide_loop import DraftRequest
    from app.services.guide_loop.publication import GuideLoopPublicationService

    db_path = str(tmp_path / "same-case-draft-race.db")
    payload_a = DraftRequest(
        base_revision="0", action="add_alias", poi_id="bathing", target_id="prince",
        alias="旧草稿问法", answer="旧草稿答案。",
        evidence={"evidence_id":"e-old", "source_ref":"旧来源"},
        effective_from="2026-11-10T00:00:00+08:00",
    )
    payload_b = DraftRequest(
        base_revision="0", action="add_alias", poi_id="bathing", target_id="prince",
        alias="新草稿问法", answer="新草稿答案。",
        evidence={"evidence_id":"e-new", "source_ref":"新来源"},
        effective_from="2026-11-10T00:00:00+08:00",
    )

    async def scenario():
        engine_a, session_a = await open_test_session(db_path)
        engine_b = session_b = None
        try:
            session_a.add(GuideLoopCase(cluster_id="same-case", category="retrieval_gap", status="open"))
            await session_a.commit()
            service_a = GuideLoopPublicationService(session_a)
            draft_a = await service_a.create_draft("same-case", payload_a)
            await session_a.commit()
            draft_a_id = draft_a.draft_id
            assert (await service_a.verify("same-case", draft_a_id))["passed"]
            await session_a.commit()

            # session_a intentionally retains its verified case snapshot while
            # a second worker replaces it with a newer, unverified draft.
            engine_b, session_b = await open_test_session(db_path)
            draft_b = await GuideLoopPublicationService(session_b).create_draft("same-case", payload_b)
            await session_b.commit()
            draft_b_id = draft_b.draft_id

            try:
                await service_a.publish("same-case", draft_a_id, "0", source_reviewed=True)
            except RuntimeError as exc:
                assert "draft changed" in str(exc)
            else:
                raise AssertionError("a stale verified draft must not publish over a newer draft")
            await session_a.rollback()

            await session_b.refresh(draft_b)
            assert draft_b.draft_id == draft_b_id
            assert draft_b.status == "draft"
            assert json.loads(draft_b.draft_json)["alias"] == "新草稿问法"
            pointer = await session_b.get(GuideLoopPointer, "bathing:prince")
            assert pointer.revision_id == "0"
            revisions = (await session_b.scalars(
                select(GuideLoopRevision).where(GuideLoopRevision.case_id == "same-case")
            )).all()
            assert revisions == []
        finally:
            await session_a.close()
            await engine_a.dispose()
            if session_b is not None:
                await session_b.close()
            if engine_b is not None:
                await engine_b.dispose()

    asyncio.run(scenario())


def test_stale_session_cannot_verify_a_replaced_draft(tmp_path):
    from app.schemas.guide_loop import DraftRequest
    from app.services.guide_loop.publication import GuideLoopPublicationService

    db_path = str(tmp_path / "verify-replaced-draft.db")

    def payload(alias: str) -> DraftRequest:
        return DraftRequest(
            base_revision="0", action="add_alias", poi_id="bathing", target_id="prince",
            alias=alias, answer="答案。", evidence={"evidence_id":"e1", "source_ref":"来源"},
            effective_from="2026-11-10T00:00:00+08:00",
        )

    async def scenario():
        engine_a, session_a = await open_test_session(db_path)
        engine_b = session_b = None
        try:
            session_a.add(GuideLoopCase(cluster_id="verify-race", category="retrieval_gap", status="open"))
            await session_a.commit()
            service_a = GuideLoopPublicationService(session_a)
            draft_a = await service_a.create_draft("verify-race", payload("旧草稿"))
            await session_a.commit()
            draft_a_id = draft_a.draft_id

            engine_b, session_b = await open_test_session(db_path)
            draft_b = await GuideLoopPublicationService(session_b).create_draft("verify-race", payload("新草稿"))
            await session_b.commit()

            try:
                await service_a.verify("verify-race", draft_a_id)
            except RuntimeError as exc:
                assert "draft changed" in str(exc)
            else:
                raise AssertionError("verification must be bound to the current draft")
            await session_a.rollback()

            await session_b.refresh(draft_b)
            assert draft_b.status == "draft"
            assert draft_b.verification_json is None
            assert json.loads(draft_b.draft_json)["alias"] == "新草稿"
        finally:
            await session_a.close()
            await engine_a.dispose()
            if session_b is not None:
                await session_b.close()
            if engine_b is not None:
                await engine_b.dispose()

    asyncio.run(scenario())


def test_stale_pointer_snapshot_cannot_save_a_draft_after_publication(tmp_path):
    from app.schemas.guide_loop import DraftRequest
    from app.services.guide_loop.publication import GuideLoopPublicationService

    db_path = str(tmp_path / "draft-after-publish-race.db")
    payload = DraftRequest(
        base_revision="0", action="add_alias", poi_id="bathing", target_id="prince",
        alias="并发问法", answer="答案。", evidence={"evidence_id":"e1", "source_ref":"来源"},
        effective_from="2026-11-10T00:00:00+08:00",
    )

    async def scenario():
        engine_a, session_a = await open_test_session(db_path)
        engine_b = session_b = None
        try:
            session_a.add(GuideLoopCase(cluster_id="draft-race", category="retrieval_gap", status="open"))
            await session_a.commit()
            stale_case = await session_a.get(GuideLoopCase, "draft-race")
            stale_pointer = GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="0")
            session_a.add(stale_pointer)
            await session_a.commit()

            engine_b, session_b = await open_test_session(db_path)
            service_b = GuideLoopPublicationService(session_b)
            draft_b = await service_b.create_draft("draft-race", payload)
            await session_b.commit()
            assert (await service_b.verify("draft-race", draft_b.draft_id))["passed"]
            await session_b.commit()
            revision = await service_b.publish("draft-race", draft_b.draft_id, "0", source_reviewed=True)
            await session_b.commit()

            assert stale_case.status == "open"
            assert stale_pointer.revision_id == "0"
            try:
                await GuideLoopPublicationService(session_a).create_draft("draft-race", payload)
            except RuntimeError as exc:
                assert "base revision is stale" in str(exc)
            else:
                raise AssertionError("an old pointer snapshot must not replace a published case")
            await session_a.rollback()

            await session_b.refresh(draft_b)
            assert draft_b.status == "published_pending_check"
            assert draft_b.draft_hash == revision.revision_id
            pointer = await session_b.get(GuideLoopPointer, "bathing:prince")
            await session_b.refresh(pointer)
            assert pointer.revision_id == revision.revision_id
        finally:
            await session_a.close()
            await engine_a.dispose()
            if session_b is not None:
                await session_b.close()
            if engine_b is not None:
                await engine_b.dispose()

    asyncio.run(scenario())


def test_stale_case_snapshot_cannot_overwrite_a_newer_draft(tmp_path):
    from app.schemas.guide_loop import DraftRequest
    from app.services.guide_loop.publication import GuideLoopPublicationService

    db_path = str(tmp_path / "draft-overwrite-race.db")

    def payload(alias: str) -> DraftRequest:
        return DraftRequest(
            base_revision="0", action="add_alias", poi_id="bathing", target_id="prince",
            alias=alias, answer="答案。", evidence={"evidence_id":"e1", "source_ref":"来源"},
            effective_from="2026-11-10T00:00:00+08:00",
        )

    async def scenario():
        engine_a, session_a = await open_test_session(db_path)
        engine_b = session_b = None
        try:
            session_a.add_all([
                GuideLoopCase(cluster_id="draft-overwrite", category="retrieval_gap", status="open"),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="0"),
            ])
            await session_a.commit()
            stale_case = await session_a.get(GuideLoopCase, "draft-overwrite")

            engine_b, session_b = await open_test_session(db_path)
            current = await GuideLoopPublicationService(session_b).create_draft("draft-overwrite", payload("当前草稿"))
            await session_b.commit()
            current_id = current.draft_id

            try:
                await GuideLoopPublicationService(session_a).create_draft("draft-overwrite", payload("过期会话草稿"))
            except RuntimeError as exc:
                assert "case changed" in str(exc)
            else:
                raise AssertionError("a stale case snapshot must not overwrite a newer draft")
            await session_a.rollback()

            await session_b.refresh(current)
            assert current.draft_id == current_id
            assert current.status == "draft"
            assert json.loads(current.draft_json)["alias"] == "当前草稿"
        finally:
            await session_a.close()
            await engine_a.dispose()
            if session_b is not None:
                await session_b.close()
            if engine_b is not None:
                await engine_b.dispose()

    asyncio.run(scenario())


def test_publish_commit_failure_keeps_revision_and_pointer_unchanged(tmp_path):
    db_path = tmp_path / "publish-commit-failure.db"
    fail_commit = {"enabled": False}
    app = FastAPI()
    app.include_router(router, prefix="/api/admin/guide-loop")

    async def db():
        engine, session = await open_test_session(str(db_path))
        original_commit = session.commit

        async def maybe_fail_commit():
            if fail_commit["enabled"]:
                raise OperationalError("injected publish commit failure", {}, Exception("disk I/O error"))
            await original_commit()

        session.commit = maybe_fail_commit
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_app_settings] = lambda: Settings(app_env="test", guide_loop_pilot_enabled=True, admin_token_secret="test-guide-loop-secret-key")
    client = TestClient(app, raise_server_exceptions=False)
    client.headers["Authorization"] = "Bearer " + create_admin_token("test-guide-loop-secret-key")
    async def seed():
        engine, session = await open_test_session(str(db_path))
        try:
            session.add(GuideLoopCase(cluster_id="commit-fail", category="retrieval_gap", status="open"))
            await session.commit()
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(seed())
    draft = client.post("/api/admin/guide-loop/cases/commit-fail/draft", json={
        "base_revision":"0", "action":"add_alias", "poi_id":"bathing", "target_id":"prince",
        "alias":"新问题别名", "answer":"已核验答案。", "evidence":{"evidence_id":"e1","source_ref":"公开方志"},
        "effective_from":"2026-11-10T00:00:00+08:00",
    }).json()
    assert client.post("/api/admin/guide-loop/cases/commit-fail/verify", json={"draft_id":draft["draft_id"]}).json()["passed"]
    fail_commit["enabled"] = True
    failed = client.post("/api/admin/guide-loop/cases/commit-fail/publish", json={"draft_id":draft["draft_id"],"base_revision":"0","source_reviewed":True})
    assert failed.status_code == 500

    async def assert_rolled_back():
        engine, session = await open_test_session(str(db_path))
        try:
            pointer = await session.get(GuideLoopPointer, "bathing:prince")
            assert pointer.revision_id == "0"
            assert await session.get(GuideLoopRevision, draft["draft_hash"]) is None
            case = await session.get(GuideLoopCase, "commit-fail")
            assert case.status == "verified"
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(assert_rolled_back())


def test_confirm_rejects_check_for_revision_older_than_active_pointer(tmp_path):
    from app.services.guide_loop.publication import GuideLoopPublicationService

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "stale-check.db"))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="case-old", category="retrieval_gap", status="published_pending_check"),
                GuideLoopRevision(revision_id="gl-old", base_revision="0", case_id="case-old", poi_id="bathing", target_id="prince", action="add_alias", alias="旧别名", answer="答复", evidence_id="e1", source_ref="https://example.org/1", effective_from=now, status="published", created_at=now),
                GuideLoopRevision(revision_id="gl-new", base_revision="gl-old", case_id="case-new", poi_id="bathing", target_id="prince", action="add_alias", alias="旧别名|新别名", answer="答复", evidence_id="e1", source_ref="https://example.org/1", effective_from=now, status="published", created_at=now),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-new"),
                GuideLoopCheck(check_id="check-old", case_id="case-old", revision_id="gl-old", decision="answer", passed=True),
            ])
            await session.commit()
            try:
                await GuideLoopPublicationService(session).confirm_live("check-old", passed=True)
            except RuntimeError as exc:
                assert "stale revision" in str(exc)
            else:
                raise AssertionError("a stale revision check must not close the case")
            case = await session.get(GuideLoopCase, "case-old")
            assert case.status == "published_pending_check"
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_old_target_check_cannot_close_same_case_after_target_switch(tmp_path):
    from app.services.guide_loop.publication import GuideLoopPublicationService

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "target-switch-check.db"))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="case-switch", category="retrieval_gap", status="published_pending_check", draft_hash="gl-new-target"),
                GuideLoopRevision(revision_id="gl-old-target", base_revision="0", case_id="case-switch", poi_id="bathing", target_id="prince", action="add_alias", alias="旧对象别名", answer="旧答复", evidence_id="e1", source_ref="方志", effective_from=now, status="published", source_reviewed=True, created_at=now),
                GuideLoopRevision(revision_id="gl-new-target", base_revision="0", case_id="case-switch", poi_id="bathing", target_id="show", action="add_alias", alias="新对象别名", answer="新答复", evidence_id="e2", source_ref="公告", effective_from=now, status="published", source_reviewed=True, created_at=now),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-old-target"),
                GuideLoopPointer(scope_key="bathing:show", poi_id="bathing", target_id="show", revision_id="gl-new-target"),
                GuideLoopCheck(check_id="check-old-target", case_id="case-switch", revision_id="gl-old-target", decision="answer", passed=True),
            ])
            await session.commit()
            try:
                await GuideLoopPublicationService(session).confirm_live("check-old-target", passed=True)
            except RuntimeError as exc:
                assert "stale case revision" in str(exc)
            else:
                raise AssertionError("a check for the old target must not close the case's newer target revision")
            case = await session.get(GuideLoopCase, "case-switch")
            assert case.status == "published_pending_check"
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_failed_live_check_reopens_case_for_repair(tmp_path):
    from app.services.guide_loop.publication import GuideLoopPublicationService

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "failed-live-check.db"))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            session.add_all([
                GuideLoopCase(cluster_id="case-repair", category="retrieval_gap", status="published_pending_check", draft_hash="gl-repair"),
                GuideLoopRevision(revision_id="gl-repair", base_revision="0", case_id="case-repair", poi_id="bathing", target_id="prince", action="add_alias", alias="花中佛像", answer="修订答案", evidence_id="e1", source_ref="公开方志", effective_from=now, status="published", created_at=now),
                GuideLoopPointer(scope_key="bathing:prince", poi_id="bathing", target_id="prince", revision_id="gl-repair"),
                GuideLoopCheck(check_id="check-failed", case_id="case-repair", revision_id="gl-repair", decision="answer", passed=True),
            ])
            await session.commit()
            case = await GuideLoopPublicationService(session).confirm_live("check-failed", passed=False)
            assert case.status == "reopened"
            check = await session.get(GuideLoopCheck, "check-failed")
            assert check.passed is True
            assert check.operator_passed is False
            assert check.operator_confirmed_at is not None
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())
