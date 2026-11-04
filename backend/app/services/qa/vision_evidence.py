from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from app.schemas.chat import VisionContext
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.rag.base import RetrievalScope


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VisionEvidenceResolution:
    resolved: ResolvedInteraction
    confirmed_title: str | None = None
    error_code: str | None = None
    error_message: str | None = None


async def resolve_vision_evidence(
    vision: VisionContext | None,
    resolved: ResolvedInteraction,
    *,
    vision_catalog,
    vision_site_id: str | None,
) -> VisionEvidenceResolution:
    """Bind confirmed image context to the current published attraction evidence."""
    if vision is None:
        return VisionEvidenceResolution(resolved=resolved)

    confirmation = vision.confirmation
    if confirmation is None:
        return VisionEvidenceResolution(
            resolved=replace(
                resolved,
                scope=None,
                active_subject=None,
                warnings=(*resolved.warnings, "vision_scope_unconfirmed"),
            )
        )

    selected_spot = None
    if vision_catalog is not None and confirmation.site_id == vision_site_id:
        try:
            catalog = await vision_catalog.list_for_site(vision_site_id)
            selected_spot = next(
                (
                    item
                    for item in catalog.entries
                    if item.site_id == vision_site_id
                    and item.spot_code == confirmation.spot_code
                    and item.published_revision_id == confirmation.published_revision_id
                ),
                None,
            )
        except Exception:
            logger.exception("Confirmed visual attraction catalog lookup failed")

    if (
        selected_spot is None
        or not selected_spot.entry_id.isdigit()
        or int(selected_spot.entry_id) < 1
    ):
        return VisionEvidenceResolution(
            resolved=replace(resolved, scope=None, active_subject=None),
            error_code="vision_confirmation_stale",
            error_message="景点已下架、更新或不属于当前景区，请重新选择。",
        )

    title = selected_spot.title
    return VisionEvidenceResolution(
        resolved=replace(
            resolved,
            scope=RetrievalScope(source_entry_id=int(selected_spot.entry_id)),
            resolution_source="selection",
            active_subject=title,
        ),
        confirmed_title=title,
    )
