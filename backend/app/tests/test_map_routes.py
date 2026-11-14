from __future__ import annotations

import asyncio
from fastapi import HTTPException

from app.api import map_routes
from app.api.map_routes import WalkingRouteRequest, _parse_polyline, get_walking_route
from app.core.config import Settings


def test_parse_polyline_returns_leaflet_latitude_longitude_pairs() -> None:
    steps = [
        {"polyline": "120.1,31.4;120.2,31.5"},
        {"polyline": "120.2,31.5;bad;190,31.5;120.3,31.6"},
    ]
    assert _parse_polyline(steps) == [[31.4, 120.1], [31.5, 120.2], [31.6, 120.3]]


def test_walk_route_uses_audited_pois_and_combines_leg_geometry(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    async def no_wait() -> None:
        return None

    async def fake_leg(_client, _key: str, origin: str, destination: str):
        calls.append((origin, destination))
        return {"distance": "120", "duration": "90", "steps": [{"polyline": f"{origin};{destination}"}]}

    monkeypatch.setattr(map_routes, "_pace_request", no_wait)
    monkeypatch.setattr(map_routes, "_fetch_leg", fake_leg)
    map_routes._CACHE.clear()

    result = asyncio.run(get_walking_route(
        WalkingRouteRequest(poi_ids=["B0FFF75IDE", "B0FFF75IDE", "B01FE197VB"]),
        Settings(amap_web_service_key="test-key"),
    ))

    assert result["available"] is True
    assert result["coordinates"][0] == [31.421388, 120.102499]
    assert len(result["coordinates"]) == 2
    assert result["distance_m"] == 120
    assert result["duration_s"] == 90
    assert len(calls) == 1


def test_walk_route_rejects_unknown_poi_ids_without_calling_amap() -> None:
    async def run() -> None:
        await get_walking_route(
            WalkingRouteRequest(poi_ids=["B0FFF75IDE", "unknown-id"]),
            Settings(amap_web_service_key="test-key"),
        )
    try:
        asyncio.run(run())
    except HTTPException as error:
        assert error.status_code == 422
        assert "尚未核验" in error.detail
    else:
        raise AssertionError("unknown POI should be rejected")


def test_walk_route_degrades_cleanly_without_server_key() -> None:
    result = asyncio.run(get_walking_route(
        WalkingRouteRequest(poi_ids=["B0FFF75IDE", "B01FE197VB"]),
        Settings(amap_web_service_key=""),
    ))
    assert result == {"available": False, "reason": "not_configured"}
