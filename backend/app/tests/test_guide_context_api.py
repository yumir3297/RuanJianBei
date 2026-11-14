import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api import guide_context
from app.core.config import Settings
from app.schemas.guide_context import GuideDecisionRequest
from app.api.weather import _normalize_alert


def test_location_contract_rejects_out_of_range_and_extra_fields():
    with pytest.raises(ValidationError):
        GuideDecisionRequest(location_hint={"lat": 91, "lng": 120, "coordinate_system": "WGS84", "mode": "real"})
    with pytest.raises(ValidationError):
        GuideDecisionRequest(unreviewed_override=True)
    with pytest.raises(ValidationError):
        GuideDecisionRequest(location_hint={"lat": float("nan"), "lng": 120, "coordinate_system": "WGS84", "mode": "real"})


def test_weather_normalizer_retains_alert_validity_metadata():
    alert = _normalize_alert({"alerts": [{
        "id": "wx-1", "effectiveTime": "2026-11-07T01:00:00+08:00",
        "expireTime": "2026-11-07T03:00:00+08:00", "status": "active",
    }]})["items"][0]
    assert alert["effectiveTime"].startswith("2026-")
    assert alert["expireTime"].startswith("2026-")
    assert alert["status"] == "active"


def test_disabled_bootstrap_has_no_db_dependency_on_data():
    result = asyncio.run(guide_context.guide_bootstrap(session=None, settings=Settings(cass_enabled=False)))
    assert result["available"] is False
    assert result["demo_enabled"] is False


def test_decision_uses_server_weather_and_ignores_client_location_as_proof(monkeypatch):
    calls = []

    async def weather(**kwargs):
        calls.append(kwargs)
        return {"source": "和风天气 QWeather", "fetched_at": datetime.now(timezone.utc).isoformat(), "weather": {"description": "晴"}, "alert": {"items": []}}

    monkeypatch.setattr(guide_context, "get_current_weather", weather)
    payload = GuideDecisionRequest(
        preferences={"remaining_minutes": 20, "interests": ["history"]},
        location_hint={"lat": 31, "lng": 120, "accuracy_m": 10, "coordinate_system": "WGS84", "mode": "real"},
    )
    result = asyncio.run(guide_context.guide_decision(payload, Settings(cass_enabled=True)))
    assert result["decision"]["action"] == "short_narration"
    assert result["evidence_status"]["location"] == "client_hint_unverified"
    assert result["context"]["interests"] == ["history"]
    assert len(calls) == 1


def test_decision_returns_weather_adaptation_from_server_source(monkeypatch):
    async def weather(**kwargs):
        now = datetime.now(timezone.utc)
        return {
            "source": "和风天气 QWeather", "fetched_at": now.isoformat(),
            "status": "available", "weather": {"iconCode": "305", "description": "小雨", "obsTime": now.isoformat()},
            "alert": {"items": []},
        }

    monkeypatch.setattr(guide_context, "get_current_weather", weather)
    result = asyncio.run(guide_context.guide_decision(
        GuideDecisionRequest(preferences={"remaining_minutes": 90}), Settings(cass_enabled=True),
    ))
    assert result["weather_adaptation"]["condition"] == "小雨"
    assert result["weather_adaptation"]["source"] == "和风天气 QWeather"
    assert result["safety_events"] == []


def test_decision_rejects_stale_published_catalog_selection(monkeypatch):
    from types import SimpleNamespace

    class Catalog:
        def __init__(self, source):
            pass

        async def list_for_site(self, site_id):
            return SimpleNamespace(digest="catalog-current", entries=[SimpleNamespace(spot_code="tower", published_revision_id="rev-3")])

    weather_calls = []

    async def weather(**kwargs):
        weather_calls.append(kwargs)
        return {"source": "和风天气 QWeather", "alert": {"items": []}}

    monkeypatch.setattr(guide_context, "PublishedAttractionCatalog", Catalog)
    monkeypatch.setattr(guide_context, "get_current_weather", weather)
    payload = GuideDecisionRequest(spot_code="tower", published_revision_id="rev-2", catalog_digest="catalog-old")
    result = asyncio.run(guide_context.guide_decision(payload, Settings(cass_enabled=True), session=None))
    assert result["available"] is False
    assert result["reason"] == "catalog_changed"
    assert weather_calls == []


def test_critical_weather_alert_preempts_narration(monkeypatch):
    async def weather(**kwargs):
        return {"source": "和风天气 QWeather", "fetched_at": datetime.now(timezone.utc).isoformat(), "weather": None, "alert": {"items": [{
            "id": "wx-1", "severity": "Severe", "effectiveTime": "2020-01-01T00:00:00Z",
            "expireTime": "2030-01-01T00:00:00Z", "headline": "大风预警",
        }]}}

    monkeypatch.setattr(guide_context, "get_current_weather", weather)
    result = asyncio.run(guide_context.guide_decision(
        GuideDecisionRequest(preferences={"remaining_minutes": 20}), Settings(cass_enabled=True),
    ))
    assert result["decision"]["action"] == "none"
    assert result["safety_events"][0]["event_id"] == "qweather:wx-1"


def test_enabling_demo_does_not_hide_live_weather_warning(monkeypatch):
    async def weather(**kwargs):
        return {"source": "和风天气 QWeather", "fetched_at": datetime.now(timezone.utc).isoformat(), "alert": {"items": [{
            "id": "wx-live", "severity": "Severe", "effectiveTime": "2020-01-01T00:00:00Z",
            "expireTime": "2030-01-01T00:00:00Z", "headline": "官方预警",
        }]}}

    monkeypatch.setattr(guide_context, "get_current_weather", weather)
    result = asyncio.run(guide_context.guide_decision(
        GuideDecisionRequest(demo_scenario_id="weather-interruption-v1"),
        Settings(cass_enabled=True, cass_demo_enabled=True),
    ))
    assert result["safety_events"][0]["event_id"] == "qweather:wx-live"
