"""Server-side Amap walking paths for the verified Lingshan POIs."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.core.deps import get_app_settings

router = APIRouter()

# Only accept coordinates audited from Amap POIs. The browser sends IDs, never
# arbitrary coordinates, and the Web Service key remains server-side.
_POI_COORDINATES: dict[str, tuple[float, float]] = {
    "B01FE00DQ6": (120.096477, 31.430194),
    "B01FE199JX": (120.099984, 31.424601),
    "B01FE199CS": (120.099569, 31.425559),
    "B01FE1997R": (120.099261, 31.426188),
    "B01FE199JN": (120.098844, 31.427190),
    "B01FE176MH": (120.102420, 31.428218),
    "B01FE197GZ": (120.103054, 31.424676),
    "B01FE199KC": (120.104609, 31.426070),
    "B01FE199EK": (120.096710, 31.428729),
    "B01FE199LG": (120.101143, 31.423182),
    "B0FFF75IDE": (120.102499, 31.421388),
    "B01FE199E0": (120.101497, 31.422725),
    "B01FE197RG": (120.101292, 31.423055),
    "B01FE197VB": (120.102248, 31.421749),
    "B0FFF0EWZU": (120.098012, 31.427949),
    "B0FFG6ROHI": (120.098781, 31.427066),
    "B01FE1997N": (120.097377, 31.428946),
    "B0FFHX4MOR": (120.096300, 31.424395),
    "B01FE19VVI": (120.102651, 31.427205),
    "B01FE197GT": (120.098366, 31.426957),
}
_CACHE: dict[tuple[str, ...], tuple[float, dict[str, Any]]] = {}
_RATE_LOCK = asyncio.Lock()
_LAST_CALL = 0.0


class WalkingRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poi_ids: list[str] = Field(min_length=2, max_length=20)


def _parse_polyline(steps: list[dict[str, Any]]) -> list[list[float]]:
    points: list[list[float]] = []
    for step in steps:
        raw = step.get("polyline")
        if not isinstance(raw, str):
            continue
        for pair in raw.split(";"):
            try:
                longitude, latitude = (float(value) for value in pair.split(",", 1))
            except (TypeError, ValueError):
                continue
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                continue
            point = [latitude, longitude]
            if not points or points[-1] != point:
                points.append(point)
    return points


async def _pace_request() -> None:
    global _LAST_CALL
    async with _RATE_LOCK:
        delay = 0.45 - (time.monotonic() - _LAST_CALL)
        if delay > 0:
            await asyncio.sleep(delay)
        _LAST_CALL = time.monotonic()


async def _fetch_leg(client: httpx.AsyncClient, key: str, origin: str, destination: str) -> dict[str, Any] | None:
    await _pace_request()
    try:
        response = await client.get(
            "https://restapi.amap.com/v3/direction/walking",
            params={"key": key, "origin": origin, "destination": destination, "output": "JSON"},
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if data.get("status") != "1":
        return None
    paths = data.get("route", {}).get("paths") or []
    return paths[0] if paths else None


@router.post("/walking-route", summary="规划已核验景点间的高德步行路径")
async def get_walking_route(
    payload: WalkingRouteRequest,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    if not settings.amap_web_service_key:
        return {"available": False, "reason": "not_configured"}
    if any(poi_id not in _POI_COORDINATES for poi_id in payload.poi_ids):
        raise HTTPException(status_code=422, detail="路线包含尚未核验的景点。")

    # Collapse repeated adjacent aliases such as entry → entrance landmark.
    poi_ids = tuple(poi_id for index, poi_id in enumerate(payload.poi_ids) if index == 0 or poi_id != payload.poi_ids[index - 1])
    if len(poi_ids) < 2:
        return {"available": False, "reason": "not_enough_stops"}

    now = time.monotonic()
    cached = _CACHE.get(poi_ids)
    if cached and now - cached[0] < 21600:
        return cached[1]

    legs: list[dict[str, Any]] = []
    all_points: list[list[float]] = []
    try:
        async with asyncio.timeout(45):
            async with httpx.AsyncClient(timeout=8.0) as client:
                for origin_id, destination_id in zip(poi_ids, poi_ids[1:]):
                    origin = _POI_COORDINATES[origin_id]
                    destination = _POI_COORDINATES[destination_id]
                    path = await _fetch_leg(
                        client,
                        settings.amap_web_service_key,
                        f"{origin[0]:.6f},{origin[1]:.6f}",
                        f"{destination[0]:.6f},{destination[1]:.6f}",
                    )
                    if path is None:
                        return {"available": False, "reason": "upstream_unavailable"}
                    points = _parse_polyline(path.get("steps") or [])
                    if len(points) < 2:
                        return {"available": False, "reason": "path_geometry_missing"}
                    all_points.extend(points[1:] if all_points and all_points[-1] == points[0] else points)
                    legs.append({
                        "distance_m": int(path.get("distance") or 0),
                        "duration_s": int(path.get("duration") or 0),
                    })
    except (httpx.HTTPError, TimeoutError):
        return {"available": False, "reason": "upstream_unavailable"}

    result = {
        "available": True,
        "provider": "Amap walking route",
        "coordinates": all_points,
        "distance_m": sum(leg["distance_m"] for leg in legs),
        "duration_s": sum(leg["duration_s"] for leg in legs),
        "legs": legs,
    }
    _CACHE[poi_ids] = (time.monotonic(), result)
    return result
