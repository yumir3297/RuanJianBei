from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.schemas.itinerary import PublishedCatalogEntryRead, PublishedCatalogResponse
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog

router = APIRouter()


@router.get("/catalog", response_model=PublishedCatalogResponse)
async def get_itinerary_catalog(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> PublishedCatalogResponse:
    snapshot = await PublishedAttractionCatalog(
        K01PublishedAttractionSource(session, site_id=settings.site_id)
    ).list_for_site(settings.site_id)
    return PublishedCatalogResponse(
        site_id=snapshot.site_id,
        digest=snapshot.digest,
        items=[PublishedCatalogEntryRead(
            site_id=item.site_id,
            spot_code=item.spot_code,
            entry_id=item.entry_id,
            published_revision_id=item.published_revision_id,
            title=item.title,
            aliases=list(item.aliases),
            source_label=item.source_label,
            latitude=item.latitude,
            longitude=item.longitude,
            coordinate_evidence_id=item.coordinate_evidence_id,
        ) for item in snapshot.entries],
    )
