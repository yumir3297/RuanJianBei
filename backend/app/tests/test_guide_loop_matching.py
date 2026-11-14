import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.auth import create_admin_token
from app.api.guide_loop import router
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.guide_loop import GuideLoopObservation
from app.services.guide_loop.matching import match_pair, rank_candidates
from app.schemas.guide_loop import QuestionContext
from app.tests.async_db import open_test_session


def context(text, *, poi=None, target=None, date=None):
    return QuestionContext(text=text, poi_id=poi, target_id=target, queried_date=date)


def test_semantic_paraphrase_reuses_when_scope_matches():
    decision = match_pair(
        context("莲花里是谁？", poi="bathing", target="prince"),
        context("花中的小孩是谁？", poi="bathing", target="prince"),
        score=0.92,
        threshold=0.82,
    )
    assert decision.decision == "reuse"
    assert decision.reason_code == "same_scope_high_similarity"


def test_cross_poi_hard_negative_is_distinct_even_with_high_score():
    decision = match_pair(
        context("莲花里是谁？", poi="bathing", target="lotus_figure"),
        context("莲花里是谁？", poi="buddha", target="lotus_figure"),
        score=0.99,
        threshold=0.82,
    )
    assert (decision.decision, decision.reason_code) == ("distinct", "poi_conflict")


def test_time_sensitive_questions_on_different_dates_are_distinct():
    decision = match_pair(
        context("今天下一场几点？", poi="bathing", target="show", date="2026-11-10"),
        context("今天下一场几点？", poi="bathing", target="show", date="2026-11-11"),
        score=0.99,
        threshold=0.82,
    )
    assert (decision.decision, decision.reason_code) == ("distinct", "date_conflict")


def test_missing_referent_cannot_be_auto_merged_by_similarity():
    decision = match_pair(
        context("那个是谁？", poi="bathing"),
        context("莲花里的小孩是谁？", poi="bathing", target="prince"),
        score=0.99,
        threshold=0.82,
    )
    assert (decision.decision, decision.reason_code) == ("clarify", "missing_target")


def test_unknown_scope_cannot_auto_merge_by_similarity():
    decision = match_pair(context("它是什么？"), context("那个是什么？"), score=0.99, threshold=0.82)
    assert (decision.decision, decision.reason_code) == ("clarify", "unknown_scope")


def test_candidate_ranker_returns_at_most_five_candidates():
    class FakeEmbedder:
        model_name = "unit-test"

        def embed(self, text):
            return [1.0, 0.0] if "莲花" in text else [0.0, 1.0]

        def embed_texts(self, texts):
            return [self.embed(text) for text in texts]

    candidates = [{"id": str(i), "text": "莲花里是谁" if i < 8 else "路线怎么走"} for i in range(8)]
    ranked = rank_candidates("莲花中的人物", candidates, FakeEmbedder(), top_k=5)
    assert len(ranked) == 5
    assert ranked[0]["id"] == "0"


def build_client(db_path, *, admin=False):
    app = FastAPI()
    app.include_router(router, prefix="/api/admin/guide-loop")

    async def override_db_session():
        engine, session = await open_test_session(str(db_path))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_app_settings] = lambda: Settings(
        app_env="test", guide_loop_pilot_enabled=True,
        admin_password="test-pass", admin_token_secret="test-guide-loop-secret-key",
    )
    client = TestClient(app)
    if admin:
        client.headers["Authorization"] = "Bearer " + create_admin_token("test-guide-loop-secret-key")
    return client


def test_observation_api_requires_admin_token(tmp_path):
    client = build_client(tmp_path / "guide-loop.db")
    response = client.post("/api/admin/guide-loop/observations", json={})
    assert response.status_code == 401


def test_event_is_idempotent_and_demand_counts_unique_sessions(tmp_path):
    db_path = tmp_path / "guide-loop.db"
    client = build_client(db_path, admin=True)
    base = {
        "cluster_id": "cluster-prince", "text": "莲花里的人是谁？", "poi_id": "bathing",
        "target_id": "prince", "unit_id": "bathing-intro", "evidence_ids": ["fact-1"],
        "result_code": "unanswered", "category": "retrieval_gap", "replay_id": "replay-001",
        "origin": "synthetic",
    }
    first = client.post("/api/admin/guide-loop/observations", json={**base, "event_id": "event-1", "session_key": "session-a"})
    duplicate = client.post("/api/admin/guide-loop/observations", json={**base, "event_id": "event-1", "session_key": "session-a"})
    second = client.post("/api/admin/guide-loop/observations", json={**base, "event_id": "event-2", "session_key": "session-a", "replay_id": "replay-002"})
    third = client.post("/api/admin/guide-loop/observations", json={**base, "event_id": "event-3", "session_key": "session-b", "replay_id": "replay-003"})
    assert [r.status_code for r in (first, duplicate, second, third)] == [201, 200, 201, 201]
    assert duplicate.json()["duplicate"] is True

    case_response = client.get("/api/admin/guide-loop/cases")
    assert case_response.status_code == 200
    case = case_response.json()[0]
    assert case["cluster_id"] == "cluster-prince"
    assert case["distinct_session_count"] == 2
    assert set(case["replay_ids"]) == {"replay-001", "replay-002", "replay-003"}

    async def count_rows():
        engine, session = await open_test_session(str(db_path))
        try:
            return len(list((await session.scalars(select(GuideLoopObservation))).all()))
        finally:
            await session.close()
            await engine.dispose()

    assert asyncio.run(count_rows()) == 3


def test_old_observations_expire_but_published_case_audit_remains(tmp_path):
    from datetime import datetime, timedelta, timezone
    from app.models.guide_loop import GuideLoopCase
    from app.repositories.guide_loop import GuideLoopRepository

    async def scenario():
        db_path = tmp_path / "retention.db"
        engine, session = await open_test_session(str(db_path))
        try:
            now = datetime(2026, 11, 10, tzinfo=timezone.utc)
            case = GuideLoopCase(cluster_id="published-case", category="stale_or_conflict", status="published_pending_check", created_at=now-timedelta(days=20), updated_at=now-timedelta(days=20))
            session.add(case)
            session.add(GuideLoopObservation(event_id="old-event", cluster_id="published-case", session_key="session", text="模拟旧问句", poi_id="bathing", target_id="show", evidence_ids_json="[]", result_code="unanswered", category="stale_or_conflict", replay_id="replay-old", origin="synthetic", created_at=now-timedelta(days=15)))
            await session.commit()
            repo = GuideLoopRepository(session, now=lambda: now)
            cases = await repo.list_cases()
            assert cases[0]["cluster_id"] == "published-case"
            assert cases[0]["observation_count"] == 0
            assert await session.get(GuideLoopObservation, "old-event") is None
            assert await session.get(GuideLoopCase, "published-case") is not None
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_reused_event_id_with_different_payload_is_rejected(tmp_path):
    db_path = tmp_path / "guide-loop-conflict.db"
    client = build_client(db_path, admin=True)
    base = {"event_id":"event-same","session_key":"session-a","cluster_id":"cluster-a","text":"问题一","poi_id":"bathing","target_id":"prince","evidence_ids":[],"result_code":"unanswered","category":"unknown","replay_id":"replay-a","origin":"synthetic"}
    assert client.post("/api/admin/guide-loop/observations", json=base).status_code == 201
    conflict = client.post("/api/admin/guide-loop/observations", json={**base,"text":"另一个问题"})
    assert conflict.status_code == 409


def test_same_cluster_rejects_cross_poi_or_target_observations(tmp_path):
    db_path = tmp_path / "cluster-scope.db"
    client = build_client(db_path, admin=True)
    base = {"event_id":"event-one","session_key":"session-a","cluster_id":"same-cluster","text":"莲花里是谁？","poi_id":"bathing","target_id":"prince","evidence_ids":[],"result_code":"unanswered","category":"unknown","replay_id":"replay-one","origin":"synthetic"}
    assert client.post("/api/admin/guide-loop/observations", json=base).status_code == 201
    wrong_poi = client.post("/api/admin/guide-loop/observations", json={**base,"event_id":"event-two","session_key":"session-b","poi_id":"buddha","target_id":"prince","replay_id":"replay-two"})
    wrong_target = client.post("/api/admin/guide-loop/observations", json={**base,"event_id":"event-three","session_key":"session-c","target_id":"show","replay_id":"replay-three"})
    assert wrong_poi.status_code == 409
    assert wrong_target.status_code == 409


def test_temporal_observations_accumulate_by_date_and_quarantine_missing_dates(tmp_path):
    db_path = tmp_path / "temporal-observations.db"
    client = build_client(db_path, admin=True)
    base = {"session_key":"session-a","cluster_id":"show-times","text":"今天下一场几点？","poi_id":"bathing","target_id":"show","evidence_ids":[],"result_code":"unanswered","category":"stale_or_conflict","replay_id":"replay-a","origin":"synthetic"}
    day_one = client.post("/api/admin/guide-loop/observations", json={"event_id":"time-one",**base,"queried_date":"2026-11-10"})
    same_day = client.post("/api/admin/guide-loop/observations", json={"event_id":"time-two",**{**base,"session_key":"session-b","replay_id":"replay-b"},"queried_date":"2026-11-10"})
    next_day = client.post("/api/admin/guide-loop/observations", json={"event_id":"time-three",**{**base,"session_key":"session-c","replay_id":"replay-c"},"queried_date":"2026-11-11"})
    missing_date = client.post("/api/admin/guide-loop/observations", json={"event_id":"time-four",**{**base,"session_key":"session-d","replay_id":"replay-d"}})
    duplicate_missing = client.post("/api/admin/guide-loop/observations", json={"event_id":"time-four",**{**base,"session_key":"session-d","replay_id":"replay-d"}})

    assert day_one.status_code == same_day.status_code == next_day.status_code == missing_date.status_code == 201
    assert day_one.json()["cluster_id"] == same_day.json()["cluster_id"] == "show-times"
    assert next_day.json()["cluster_id"] != "show-times"
    assert next_day.json()["clarification_required"] is False
    assert missing_date.json()["cluster_id"] not in {"show-times", next_day.json()["cluster_id"]}
    assert missing_date.json()["clarification_required"] is True
    assert missing_date.json()["reason_code"] == "missing_date"
    assert duplicate_missing.status_code == 200
    assert duplicate_missing.json()["duplicate"] is True
    assert duplicate_missing.json()["cluster_id"] == missing_date.json()["cluster_id"]


def test_observation_ingest_purges_expired_samples_before_recording(tmp_path):
    from datetime import datetime, timedelta, timezone
    from app.models.guide_loop import GuideLoopCase, GuideLoopObservation
    from app.repositories.guide_loop import GuideLoopRepository
    from app.schemas.guide_loop import ObservationCreate

    async def scenario():
        now = datetime(2026, 11, 11, tzinfo=timezone.utc)
        engine, session = await open_test_session(str(tmp_path / "ingest-retention.db"))
        try:
            session.add(GuideLoopCase(cluster_id="old", category="unknown", status="open"))
            session.add(GuideLoopObservation(event_id="expired", cluster_id="old", session_key="s0", text="旧问题", poi_id="bathing", target_id="prince", unit_id=None, evidence_ids_json="[]", result_code="unanswered", category="unknown", replay_id="r0", origin="synthetic", created_at=now-timedelta(days=15)))
            await session.commit()
            payload = ObservationCreate(event_id="fresh", session_key="s1", cluster_id="new", text="新问题", poi_id="bathing", target_id="show", result_code="unanswered", category="unknown", replay_id="r1", origin="synthetic")
            await GuideLoopRepository(session, now=lambda: now).record(payload)
            assert await session.get(GuideLoopObservation, "expired") is None
            assert await session.get(GuideLoopObservation, "fresh") is not None
        finally:
            await session.close(); await engine.dispose()
    asyncio.run(scenario())


def test_replay_requires_admin_and_delegates_to_visitor_pipeline(tmp_path, monkeypatch):
    from fastapi.responses import StreamingResponse
    from app.api import chat

    calls = []
    async def fake_stream(payload, request, session, settings):
        calls.append((payload.query, payload.guide_loop.poi_id, payload.text_only))
        return StreamingResponse(iter(['event: done\ndata: {}\n\n']), media_type='text/event-stream')
    monkeypatch.setattr(chat, '_stream_chat', fake_stream)
    body = {'query': '莲花里是谁', 'session_id': 'replay-test', 'text_only': True, 'guide_loop': {'poi_id': 'bathing'}}
    anonymous = build_client(tmp_path / 'replay.db')
    assert anonymous.post('/api/admin/guide-loop/replay', json=body).status_code == 401
    assert calls == []
    admin = build_client(tmp_path / 'replay.db', admin=True)
    assert admin.post('/api/admin/guide-loop/replay', json={**body, 'text_only': False}).status_code == 422
    response = admin.post('/api/admin/guide-loop/replay', json=body)
    assert response.status_code == 200
    assert 'event: done' in response.text
    assert calls == [('莲花里是谁', 'bathing', True)]


def test_pilot_routes_are_unavailable_when_disabled_or_in_production(tmp_path):
    client = build_client(tmp_path / 'pilot-gate.db', admin=True)
    for env, enabled in [('test', False), ('production', True)]:
        client.app.dependency_overrides[get_app_settings] = lambda: Settings(
            app_env=env, guide_loop_pilot_enabled=enabled,
            admin_password='test-pass', admin_token_secret='test-guide-loop-secret-key',
        )
        assert client.get('/api/admin/guide-loop/cases').status_code == 404
