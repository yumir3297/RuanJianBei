from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.itinerary import TourSnapshotV2
from app.services.itinerary.provenance import normalize_snapshot_provenance


def test_untrusted_draft_provenance_is_normalized_from_server_facts():
    stop_id = str(uuid4())
    previous = TourSnapshotV2.model_validate({
        "schema_version": 2,
        "stops": [{"stop_id": stop_id, "kind": "visit", "spot_code": "A", "name": "旧标题",
                   "source_entry_id": "old-entry", "source_revision_id": "old-revision",
                   "duration_minutes": 30, "duration_basis": "source",
                   "evidence": [{"evidence_type": "published_content", "reference_id": "duration-doc", "label": "已发布时长"}],
                   "created_by": "template"}],
    })
    incoming_raw = previous.model_dump(mode="json")
    stop = incoming_raw["stops"][0]
    stop.update(name="游客篡改标题", source_entry_id="forged-entry", source_revision_id="forged-revision",
                duration_basis="estimate", created_by="ai")
    stop["evidence"][0]["reference_id"] = "forged-evidence"
    incoming_raw["stops"].append({
        "stop_id": str(uuid4()), "kind": "visit", "spot_code": "B", "name": "伪造标题",
        "source_entry_id": "fake", "source_revision_id": "fake-revision",
        "duration_minutes": 20, "duration_basis": "estimate",
        "evidence": [{"evidence_type": "published_content", "reference_id": "fake", "label": "伪造"}],
        "created_by": "ai",
    })
    incoming = TourSnapshotV2.model_validate(incoming_raw)
    entries = {
        "A": SimpleNamespace(title="甲景点", entry_id="entry-a", published_revision_id="revision-a"),
        "B": SimpleNamespace(title="乙景点", entry_id="entry-b", published_revision_id="revision-b"),
    }

    normalized = normalize_snapshot_provenance(incoming, previous=previous, catalog_entries=entries)

    original, added = normalized.stops
    assert (original.name, original.source_entry_id, original.source_revision_id) == ("甲景点", "entry-a", "revision-a")
    assert original.duration_basis == "source"
    assert original.evidence[0].reference_id == "duration-doc"
    assert original.created_by == "template"
    assert (added.name, added.source_entry_id, added.source_revision_id) == ("乙景点", "entry-b", "revision-b")
    assert added.duration_basis == "user"
    assert added.evidence[0].evidence_type == "visitor_input"
    assert added.created_by == "manual"


def test_changed_duration_and_new_route_leg_do_not_inherit_forged_evidence():
    first, second = str(uuid4()), str(uuid4())
    previous = TourSnapshotV2.model_validate({
        "schema_version": 2,
        "stops": [
            {"stop_id": first, "kind": "visit", "spot_code": "A", "name": "甲", "duration_minutes": 30,
             "duration_basis": "source", "evidence": [{"evidence_type": "published_content", "reference_id": "source-1"}]},
            {"stop_id": second, "kind": "visit", "spot_code": "B", "name": "乙", "duration_minutes": 20,
             "duration_basis": "user"},
        ],
        "legs": [{"from_stop_id": first, "to_stop_id": second, "duration_minutes": 10,
                  "duration_basis": "estimate", "evidence": [{"evidence_type": "estimate", "label": "旧路段估计"}]}],
    })
    incoming_raw = previous.model_dump(mode="json")
    incoming_raw["stops"][0].update(duration_minutes=35, duration_basis="source",
                                     evidence=[{"evidence_type": "published_content", "reference_id": "fake"}])
    incoming_raw["legs"][0].update(duration_minutes=99, duration_basis="estimate",
                                    evidence=[{"evidence_type": "estimate", "label": "用户伪造"}])
    incoming = TourSnapshotV2.model_validate(incoming_raw)

    normalized = normalize_snapshot_provenance(incoming, previous=previous)

    assert normalized.stops[0].duration_basis == "user"
    assert normalized.stops[0].evidence[0].evidence_type == "visitor_input"
    assert normalized.legs[0].duration_minutes is None
    assert normalized.legs[0].duration_basis == "unknown"
    assert normalized.legs[0].evidence == []
