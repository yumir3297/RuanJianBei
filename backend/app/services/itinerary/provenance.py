from __future__ import annotations

from typing import Literal, Mapping

from app.schemas.itinerary import EvidenceReference, TourSnapshotV2
from app.services.itinerary.catalog import PublishedAttraction


def normalize_snapshot_provenance(
    snapshot: TourSnapshotV2,
    *,
    previous: TourSnapshotV2 | None = None,
    catalog_entries: Mapping[str, PublishedAttraction] | None = None,
    new_stop_created_by: Literal["manual", "ai", "template"] = "manual",
) -> TourSnapshotV2:
    """Replace client claims about sources/evidence with facts derived by the server.

    Unchanged stops and legs inherit their previously persisted provenance. New or
    changed durations are treated as visitor supplied; newly submitted stops are
    manual. Route legs have no authoritative source in V01, so changed legs become
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
            if old.duration_minutes == stop.duration_minutes:
                stop.duration_basis = old.duration_basis
                stop.evidence = old.evidence
            else:
                stop.duration_basis = "user" if stop.duration_minutes is not None else "unknown"
                stop.evidence = ([EvidenceReference(evidence_type="visitor_input", label="游客填写的停留时长")]
                                 if stop.duration_minutes is not None else [])
        else:
            stop.created_by = new_stop_created_by
            stop.duration_basis = "user" if stop.duration_minutes is not None else "unknown"
            stop.evidence = ([EvidenceReference(evidence_type="visitor_input", label="游客填写的停留时长")]
                             if stop.duration_minutes is not None else [])

    old_legs = {
        (str(leg.from_stop_id), str(leg.to_stop_id)): leg
        for leg in previous.legs
    } if previous else {}
    for leg in result.legs:
        old = old_legs.get((str(leg.from_stop_id), str(leg.to_stop_id)))
        if old is not None and old.duration_minutes == leg.duration_minutes:
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
