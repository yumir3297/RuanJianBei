from __future__ import annotations

import asyncio
import json

import pytest

from app.core.config import Settings
from app.schemas.itinerary import RemoveStop, SetDuration, TourSnapshotV2
from app.services.itinerary.catalog import CatalogSnapshot, PublishedAttraction
from app.services.itinerary.candidates import CandidateSearchTooLarge, select_candidate
from app.services.itinerary.intent import IntentError, IntentUnavailable, ItineraryIntentService


def test_intent_service_fails_closed_when_provider_is_not_configured():
    async def scenario():
        service = ItineraryIntentService()
        catalog = CatalogSnapshot(site_id="lingshan", entries=(), digest="empty-catalog")
        with pytest.raises(IntentUnavailable, match="尚未配置"):
            await service.propose("增加一个景点", TourSnapshotV2(), catalog,
                Settings(llm_provider="stub", llm_api_key="", llm_base_url="", llm_model=""))

    asyncio.run(scenario())


def _snapshot(*, required_spots=None, walking_preference=None):
    return TourSnapshotV2.model_validate({
        "schema_version": 2,
        "constraints": {"required_spots": required_spots or [], "walking_preference": walking_preference},
        "stops": [
            {"stop_id": "00000000-0000-0000-0000-000000000001", "kind": "visit", "spot_code": "A", "name": "甲景点", "duration_minutes": 30, "duration_basis": "user"},
            {"stop_id": "00000000-0000-0000-0000-000000000002", "kind": "visit", "spot_code": "B", "name": "乙景点", "duration_minutes": 30, "duration_basis": "user"},
        ],
    })


def test_candidate_selector_prefers_hard_valid_candidate_over_smaller_conflicting_edit():
    snapshot = _snapshot(required_spots=["A"])
    remove_required = RemoveStop(type="remove_stop", stop_id="00000000-0000-0000-0000-000000000001")
    adjust_optional = SetDuration(type="set_duration", stop_id="00000000-0000-0000-0000-000000000002", duration_minutes=20)

    selected = select_candidate(snapshot, [[remove_required], [adjust_optional]], required_operations=[], catalog_spot_codes={"A", "B"})

    assert selected.operations == (adjust_optional,)
    assert selected.hard_conflicts == 0
    assert selected.mutation.validation == "unverified"


def test_candidate_selector_prefers_fewer_unrelated_changes_then_fewer_changed_stops():
    snapshot = _snapshot()
    required = SetDuration(type="set_duration", stop_id="00000000-0000-0000-0000-000000000002", duration_minutes=45)
    extra_remove = RemoveStop(type="remove_stop", stop_id="00000000-0000-0000-0000-000000000001")

    selected = select_candidate(snapshot, [[required, extra_remove], [required]], required_operations=[required], catalog_spot_codes={"A", "B"})

    assert selected.operations == (required,)
    assert selected.unrelated_changes == 0
    assert selected.changed_stops == 1


def test_candidate_selector_uses_less_walking_only_as_approximate_tiebreaker():
    snapshot = _snapshot(walking_preference="少走路")
    remove_visit = RemoveStop(type="remove_stop", stop_id="00000000-0000-0000-0000-000000000001")
    shorten_visit = SetDuration(type="set_duration", stop_id="00000000-0000-0000-0000-000000000001", duration_minutes=20)

    selected = select_candidate(snapshot, [[shorten_visit], [remove_visit]], required_operations=[], catalog_spot_codes={"A", "B"})

    assert selected.operations == (remove_visit,)
    assert selected.preference_score == -1


def test_candidate_selector_accepts_less_walking_preference_from_current_request():
    snapshot = _snapshot()
    remove_visit = RemoveStop(type="remove_stop", stop_id="00000000-0000-0000-0000-000000000001")
    shorten_visit = SetDuration(type="set_duration", stop_id="00000000-0000-0000-0000-000000000001", duration_minutes=20)

    selected = select_candidate(snapshot, [[shorten_visit], [remove_visit]], required_operations=[],
                                catalog_spot_codes={"A", "B"}, prefer_less_walking=True)

    assert selected.operations == (remove_visit,)
    assert selected.preference_score == -1


def test_candidate_selector_rejects_search_space_over_two_hundred():
    snapshot = _snapshot()
    operations = [SetDuration(type="set_duration", stop_id="00000000-0000-0000-0000-000000000002", duration_minutes=value)
                  for value in range(1, 202)]

    with pytest.raises(CandidateSearchTooLarge, match="方案过多"):
        select_candidate(snapshot, [[operation] for operation in operations], required_operations=[], catalog_spot_codes={"A", "B"})


def test_intent_service_selects_candidate_after_shared_reducer_validation(monkeypatch):
    required = {"type": "set_duration", "stop_id": "00000000-0000-0000-0000-000000000002", "duration_minutes": 45}
    conflicting = {"type": "remove_stop", "stop_id": "00000000-0000-0000-0000-000000000001"}
    payload = {
        "result": "operations",
        "required_operations": [required],
        "alternatives": [{"operations": [required, conflicting]}, {"operations": [required]}],
    }

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return None
        async def post(self, *_args, **_kwargs): return FakeResponse()

    monkeypatch.setattr("app.services.itinerary.intent.httpx.AsyncClient", lambda **_kwargs: FakeClient())
    catalog = CatalogSnapshot("lingshan", (
        PublishedAttraction("lingshan", "A", "entry-a", "revision-a", "甲景点"),
        PublishedAttraction("lingshan", "B", "entry-b", "revision-b", "乙景点"),
    ), "catalog-digest")

    async def scenario():
        return await ItineraryIntentService().propose("把乙景点停留改为 45 分钟", _snapshot(required_spots=["A"]), catalog,
            Settings(llm_provider="openai", llm_api_key="test", llm_base_url="https://example.test", llm_model="test"))

    result = asyncio.run(scenario())
    assert result["status"] == "ready"
    assert result["operations"] == [required]
    assert result["validation"]["selection"]["candidate_count"] == 2
    assert result["candidate"]["stops"][1]["duration_minutes"] == 45
    assert result["candidate"]["stops"][1]["duration_basis"] == "estimate"
    assert result["candidate"]["stops"][1]["evidence"][0]["evidence_type"] == "estimate"


def test_intent_service_retries_one_invalid_format_then_accepts_valid_response(monkeypatch):
    valid_payload = {"result": "operations", "operations": [
        {"type": "set_duration", "stop_id": "00000000-0000-0000-0000-000000000002", "duration_minutes": 45}
    ]}
    contents = iter(["not json", json.dumps(valid_payload)])
    requests = []

    class FakeResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": self.content}}]}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return None
        async def post(self, _url, **kwargs):
            requests.append(kwargs["json"])
            return FakeResponse(next(contents))

    monkeypatch.setattr("app.services.itinerary.intent.httpx.AsyncClient", lambda **_kwargs: FakeClient())
    catalog = CatalogSnapshot("lingshan", (
        PublishedAttraction("lingshan", "A", "entry-a", "revision-a", "甲景点"),
        PublishedAttraction("lingshan", "B", "entry-b", "revision-b", "乙景点"),
    ), "catalog-digest")

    async def scenario():
        return await ItineraryIntentService().propose("把乙景点改为 45 分钟", _snapshot(), catalog,
            Settings(llm_provider="openai", llm_api_key="test", llm_base_url="https://example.test", llm_model="test"))

    result = asyncio.run(scenario())
    assert result["status"] == "ready"
    assert len(requests) == 2
    assert any("严格 JSON" in message["content"] for message in requests[1]["messages"])


def test_intent_service_fails_after_second_invalid_format_without_third_attempt(monkeypatch):
    calls = 0

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "not json"}}]}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return None
        async def post(self, *_args, **_kwargs):
            nonlocal calls
            calls += 1
            return FakeResponse()

    monkeypatch.setattr("app.services.itinerary.intent.httpx.AsyncClient", lambda **_kwargs: FakeClient())
    catalog = CatalogSnapshot("lingshan", (), "empty-catalog")

    async def scenario():
        return await ItineraryIntentService().propose("增加景点", _snapshot(), catalog,
            Settings(llm_provider="openai", llm_api_key="test", llm_base_url="https://example.test", llm_model="test"))

    with pytest.raises(IntentError, match="符合行程规则"):
        asyncio.run(scenario())
    assert calls == 2
