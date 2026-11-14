from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.weather import get_current_weather
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.schemas.guide_context import GuideDecisionRequest
from app.services.guide_context.policy import make_decision
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog

router = APIRouter()


@router.get("/bootstrap")
async def guide_bootstrap(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    if not settings.cass_enabled:
        return {"available": False, "enabled": False, "demo_enabled": False, "site_id": settings.site_id}
    catalog = await PublishedAttractionCatalog(
        K01PublishedAttractionSource(session, site_id=settings.site_id)
    ).list_for_site(settings.site_id)
    return {
        "available": True,
        "enabled": True,
        "demo_enabled": settings.cass_demo_enabled,
        "site_id": settings.site_id,
        "catalog_digest": catalog.digest,
        "catalog": [{
            "spot_code": item.spot_code,
            "published_revision_id": item.published_revision_id,
            "title": item.title,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "coordinate_evidence_id": item.coordinate_evidence_id,
            "coordinate_system": item.coordinate_system,
            "environment": item.environment,
            "environment_source_id": item.environment_source_id,
        } for item in catalog.entries],
        "verified_local_resources": [],
    }


@router.post("/decision")
async def guide_decision(
    payload: GuideDecisionRequest,
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not settings.cass_enabled or (payload.demo_scenario_id and not settings.cass_demo_enabled):
        return {"available": False, "reason": "cass_disabled", "safety_events": []}

    catalog_digest = None
    selected_spot = None
    if payload.spot_code:
        catalog = await PublishedAttractionCatalog(
            K01PublishedAttractionSource(session, site_id=settings.site_id)
        ).list_for_site(settings.site_id)
        selected_spot = next((item for item in catalog.entries if item.spot_code == payload.spot_code), None)
        if (
            selected_spot is None
            or not payload.catalog_digest
            or payload.catalog_digest != catalog.digest
            or payload.published_revision_id != selected_spot.published_revision_id
        ):
            return {"available": False, "reason": "catalog_changed", "safety_events": []}
        catalog_digest = catalog.digest

    # Weather and alerts are fetched server-side; client-supplied context is never accepted as evidence.
    weather = await get_current_weather(lat=None, lon=None, settings=settings)
    now = datetime.now(timezone.utc)
    digest = payload.model_dump(mode="json", exclude={"snapshot_id"})
    result = make_decision({
        "snapshot_id": payload.snapshot_id,
        "demo_scenario_id": payload.demo_scenario_id,
        "preferences": payload.preferences.model_dump(),
        "playback_busy": payload.playback_busy,
        "spot_code": selected_spot.spot_code if selected_spot else None,
        "published_revision_id": selected_spot.published_revision_id if selected_spot else None,
        "catalog_digest": catalog_digest,
        "tour_session_id": payload.tour_session_id,
        "expected_tour_version": payload.expected_tour_version,
        "progress_version": payload.progress_version,
    }, weather, now)
    result["context_digest"] = hashlib.sha256(
        json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result["context"] = {
        "spot_code": selected_spot.spot_code if selected_spot else None,
        "published_revision_id": selected_spot.published_revision_id if selected_spot else None,
        "catalog_digest": catalog_digest,
        "interests": payload.preferences.interests,
        "remaining_minutes": payload.preferences.remaining_minutes,
        "tour_context_source": "visitor_snapshot_unverified" if payload.tour_session_id else None,
        "playback_busy": payload.playback_busy,
    }
    return result
