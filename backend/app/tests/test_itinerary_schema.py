import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.itinerary import TourSnapshotV2, upgrade_snapshot


class ItinerarySchemaTests(unittest.TestCase):
    def test_v2_snapshot_requires_stable_stop_ids_and_has_strict_fields(self):
        generated = TourSnapshotV2.model_validate({"schema_version": 2, "stops": [{"kind": "visit", "name": "梵宫"}]})
        self.assertIsNotNone(generated.stops[0].stop_id)
        with self.assertRaises(ValidationError):
            TourSnapshotV2.model_validate({
                "schema_version": 2,
                "stops": [{"stop_id": str(uuid4()), "kind": "visit", "name": "梵宫", "owner_id": "victim"}],
            })

    def test_unknown_duration_is_nullable_and_no_authority_flags_are_accepted(self):
        item = TourSnapshotV2.model_validate({
            "schema_version": 2,
            "stops": [{"stop_id": str(uuid4()), "kind": "visit", "name": "未解析地点",
                       "duration_minutes": None, "duration_basis": "unknown"}],
        })
        self.assertIsNone(item.stops[0].spot_code)
        self.assertIsNone(item.stops[0].duration_minutes)
        with self.assertRaises(ValidationError):
            TourSnapshotV2.model_validate({
                "schema_version": 2,
                "stops": [{"stop_id": str(uuid4()), "kind": "visit", "name": "梵宫", "resolved": True}],
            })

    def test_legacy_snapshot_upgrades_without_promoting_legacy_ids_to_spot_codes(self):
        old = {
            "constraints": {"available_minutes": 180, "interests": ["建筑"]},
            "stops": [{"spot_id": "42", "name": "梵宫", "resolved": True, "published_content_version": "v7"}],
            "source": "preset",
            "source_references": [],
        }
        upgraded = upgrade_snapshot(old)
        self.assertEqual(upgraded.schema_version, 2)
        self.assertEqual(upgraded.constraints.available_minutes, 180)
        self.assertIsNone(upgraded.stops[0].spot_code)
        self.assertIsNone(upgraded.stops[0].source_entry_id)
        self.assertIsNone(upgraded.stops[0].source_revision_id)
        self.assertEqual(upgraded.stops[0].legacy_spot_id, "42")
        self.assertEqual(upgraded.stops[0].legacy_content_version, "v7")
