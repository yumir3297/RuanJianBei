from __future__ import annotations

from typing import Literal, Mapping

from app.schemas.itinerary import EvidenceReference, TourSnapshotV2
from app.services.itinerary.catalog import PublishedAttraction


def same_stop_location(old, new) -> bool:
    if old.kind != new.kind or old.spot_code != new.spot_code:
        return False
    return old.kind != "visit" or old.spot_code is not None or old.name == new.name


def mark_inherited_duration_unverified(stop) -> None:
    stop.duration_basis = "estimate" if stop.duration_minutes is not None else "unknown"
    stop.evidence = ([EvidenceReference(evidence_type="estimate", label="景点变更后原停留时长需重新确认")]
                     if stop.duration_minutes is not None else [])


def sanitize_replaced_locations(snapshot: TourSnapshotV2, previous: TourSnapshotV2) -> tuple[TourSnapshotV2, bool]:
    """Remove evidence attached to a previous location from persisted proposals."""
    result = snapshot.model_copy(deep=True)
    old_stops = {str(stop.stop_id): stop for stop in previous.stops}
    changed = set()
    for stop in result.stops:
        old = old_stops.get(str(stop.stop_id))
        if old is not None and not same_stop_location(old, stop):
            changed.add(str(stop.stop_id))
            if stop.duration_minutes == old.duration_minutes:
                mark_inherited_duration_unverified(stop)
            else:
                _set_submitted_duration_provenance(stop, "ai")
    for leg in result.legs:
        if str(leg.from_stop_id) in changed or str(leg.to_stop_id) in changed:
            leg.duration_minutes = None
            leg.duration_basis = "unknown"
            leg.evidence = []
    return result, bool(changed)


def normalize_snapshot_provenance(
    snapshot: TourSnapshotV2,
    *,
    previous: TourSnapshotV2 | None = None,
    catalog_entries: Mapping[str, PublishedAttraction] | None = None,
    new_stop_created_by: Literal["manual", "ai", "template"] = "manual",
) -> TourSnapshotV2:
    """Replace client claims about sources/evidence with facts derived by the server.

    Unchanged stops and legs inherit their previously persisted provenance. New or
    changed durations are attributed to the submission path; newly submitted stops
    are manual unless the server is applying an AI proposal. Route legs have no authoritative source in V01, so changed legs become
    unknown until a server backed route source exists.
    """
    result = snapshot.model_copy(deep=True)
    old_stops = {str(stop.stop_id): stop for stop in previous.stops} if previous else {}
    for stop in result.stops:
        old = old_stops.get(str(stop.stop_id))
        if stop.kind == "visit" and stop.spot_code:
            entry = (catalog_entries or {}).get(stop.spot_code)
            if entry is not None:
                stop.name = entry.title
                stop.source_entry_id = entry.entry_id
                stop.source_revision_id = entry.published_revision_id
                stop.legacy_spot_id = None
                stop.legacy_content_version = None
            elif catalog_entries is None and old is not None and old.spot_code == stop.spot_code:
                stop.source_entry_id = old.source_entry_id
                stop.source_revision_id = old.source_revision_id
                stop.legacy_spot_id = old.legacy_spot_id
                stop.legacy_content_version = old.legacy_content_version
            elif catalog_entries is not None or old is None or old.spot_code != stop.spot_code:
                stop.source_entry_id = None
                stop.source_revision_id = None
                stop.legacy_spot_id = None
                stop.legacy_content_version = None
        else:
            stop.source_entry_id = None
            stop.source_revision_id = None
            if stop.kind == "rest" or old is None or old.spot_code != stop.spot_code:
                stop.legacy_spot_id = None
                stop.legacy_content_version = None
            else:
                stop.legacy_spot_id = old.legacy_spot_id
                stop.legacy_content_version = old.legacy_content_version

        if old is not None:
            stop.created_by = old.created_by
            if not same_stop_location(old, stop) and old.duration_minutes == stop.duration_minutes:
                mark_inherited_duration_unverified(stop)
            elif old.duration_minutes == stop.duration_minutes:
                stop.duration_basis = old.duration_basis
                stop.evidence = old.evidence
            else:
                _set_submitted_duration_provenance(stop, new_stop_created_by)
        else:
            stop.created_by = new_stop_created_by
            _set_submitted_duration_provenance(stop, new_stop_created_by)

    old_legs = {
        (str(leg.from_stop_id), str(leg.to_stop_id)): leg
        for leg in previous.legs
    } if previous else {}
    new_stops = {str(stop.stop_id): stop for stop in result.stops}
    for leg in result.legs:
        old = old_legs.get((str(leg.from_stop_id), str(leg.to_stop_id)))
        endpoints_unchanged = all(
            stop_id in old_stops and stop_id in new_stops
            and same_stop_location(old_stops[stop_id], new_stops[stop_id])
            for stop_id in (str(leg.from_stop_id), str(leg.to_stop_id))
        )
        if old is not None and endpoints_unchanged and old.duration_minutes == leg.duration_minutes:
            leg.duration_basis = old.duration_basis
            leg.evidence = old.evidence
        else:
            leg.duration_minutes = None
            leg.duration_basis = "unknown"
            leg.evidence = []

    if previous is None:
        result.source = "manual"
        result.source_references = []
    else:
        result.source = previous.source
        result.source_references = previous.source_references
    return result


def _set_submitted_duration_provenance(stop, actor: str) -> None:
    if stop.duration_minutes is None:
        stop.duration_basis = "unknown"
        stop.evidence = []
    elif actor == "ai":
        stop.duration_basis = "estimate"
        stop.evidence = [EvidenceReference(evidence_type="estimate", label="AI 建议的停留时长，需游客确认")]
    else:
        stop.duration_basis = "user"
        stop.evidence = [EvidenceReference(evidence_type="visitor_input", label="游客填写的停留时长")]
