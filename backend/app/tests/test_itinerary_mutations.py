import unittest
from uuid import uuid4

from pydantic import TypeAdapter

from app.schemas.itinerary import ItineraryOperation, TourSnapshotV2
from app.services.itinerary.mutations import apply_manual_operations

operation_adapter = TypeAdapter(ItineraryOperation)


def _snapshot(**overrides) -> TourSnapshotV2:
    data = {
        "schema_version": 2,
        "constraints": {"available_minutes": 120, "required_spots": ["LS-01"]},
        "stops": [{
            "stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-01",
            "name": "梵宫", "duration_minutes": 30, "duration_basis": "user",
        }],
        "legs": [],
    }
    data.update(overrides)
    return TourSnapshotV2.model_validate(data)


class ItineraryMutationTests(unittest.TestCase):
    def test_ai_cannot_add_or_replace_a_visit_without_published_spot_code(self):
        snapshot = _snapshot()
        for raw in (
            {"type": "add_visit", "name": "未经核实的景点"},
            {"type": "replace_visit", "stop_id": str(snapshot.stops[0].stop_id), "name": "未经核实的景点"},
        ):
            with self.subTest(operation=raw["type"]):
                operation = operation_adapter.validate_python(raw)
                result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"}, actor="ai")
                self.assertEqual(result.validation, "conflict")
                self.assertEqual(result.snapshot, snapshot)
        manual = operation_adapter.validate_python({"type": "add_visit", "name": "游客自填地点"})
        self.assertEqual(apply_manual_operations(snapshot, [manual], catalog_spot_codes={"LS-01"}).validation, "unverified")

    def test_ai_proposed_duration_is_not_reported_as_verified(self):
        snapshot = _snapshot()
        operation = operation_adapter.validate_python({"type": "set_duration", "stop_id": str(snapshot.stops[0].stop_id),
                                                       "duration_minutes": 45})
        result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"}, actor="ai")
        self.assertEqual(result.snapshot.stops[0].duration_basis, "estimate")
        self.assertEqual(result.validation, "unverified")

    def test_add_visit_is_resolved_through_the_provided_catalog(self):
        snapshot = _snapshot()
        operation = operation_adapter.validate_python({
            "type": "add_visit", "name": "五印坛城", "spot_code": "LS-02", "duration_minutes": 20,
        })
        result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01", "LS-02"})
        self.assertEqual(len(result.snapshot.stops), 2)
        self.assertEqual(result.snapshot.stops[1].spot_code, "LS-02")
        self.assertEqual(result.validation, "unverified")
        self.assertEqual(result.diff[0].kind, "added")

    def test_same_snapshot_and_operation_sequence_produce_same_new_stop_id(self):
        snapshot = _snapshot()
        operation = operation_adapter.validate_python({"type": "add_rest", "duration_minutes": 15})
        first = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"})
        second = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"})
        self.assertEqual(first.snapshot.stops[-1].stop_id, second.snapshot.stops[-1].stop_id)

    def test_reject_unknown_spot_code_without_changing_the_input_snapshot(self):
        snapshot = _snapshot()
        operation = operation_adapter.validate_python({"type": "add_visit", "name": "伪造景点", "spot_code": "FAKE-404"})
        result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"})
        self.assertEqual(result.validation, "conflict")
        self.assertEqual(len(result.snapshot.stops), 1)
        self.assertIn("目录", result.conflicts[0])

    def test_locked_stop_cannot_be_removed_by_manual_operation(self):
        snapshot = _snapshot(stops=[{
            "stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-01", "name": "梵宫",
            "duration_minutes": 30, "duration_basis": "user", "locked_fields": ["stop"],
        }])
        operation = operation_adapter.validate_python({"type": "remove_stop", "stop_id": str(snapshot.stops[0].stop_id)})
        result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01"})
        self.assertEqual(result.validation, "conflict")
        self.assertEqual(len(result.snapshot.stops), 1)
        self.assertIn("锁定", result.conflicts[0])

    def test_excluded_stop_is_reported_as_a_hard_conflict(self):
        snapshot = _snapshot(constraints={
            "available_minutes": 120, "required_spots": ["LS-01"], "excluded_spots": ["LS-02"],
        })
        operation = operation_adapter.validate_python({"type": "add_visit", "name": "灵山梵宫", "spot_code": "LS-02"})
        result = apply_manual_operations(snapshot, [operation], catalog_spot_codes={"LS-01", "LS-02"})
        self.assertEqual(result.validation, "conflict")
        self.assertEqual(len(result.snapshot.stops), 1)
        self.assertIn("排除", result.conflicts[0])

    def test_unknown_travel_time_is_unverified_not_zero(self):
        snapshot = _snapshot(stops=[
            {"stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-01", "name": "梵宫",
             "duration_minutes": 30, "duration_basis": "user"},
            {"stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-02", "name": "五印坛城",
             "duration_minutes": 20, "duration_basis": "user"},
        ])
        result = apply_manual_operations(snapshot, [], catalog_spot_codes={"LS-01", "LS-02"})
        self.assertEqual(result.validation, "unverified")
        self.assertEqual(result.known_minutes, 50)

    def test_missing_total_budget_is_unverified_even_when_stop_duration_is_known(self):
        snapshot = _snapshot(constraints={"required_spots": ["LS-01"]})
        result = apply_manual_operations(snapshot, [], catalog_spot_codes={"LS-01"})
        self.assertEqual(result.validation, "unverified")
        self.assertEqual(result.known_minutes, 30)

    def test_constraint_changes_appear_in_the_structured_diff(self):
        snapshot = _snapshot()
        changed = operation_adapter.validate_python({
            "type": "update_constraints", "constraints": {
                "available_minutes": 90, "required_spots": ["LS-01"], "walking_preference": "少走路",
            },
        })
        result = apply_manual_operations(snapshot, [changed], catalog_spot_codes={"LS-01"})
        constraint_diff = next(item for item in result.diff if item.kind == "constraints")
        self.assertEqual(constraint_diff.before["available_minutes"], 120)
        self.assertEqual(constraint_diff.after["available_minutes"], 90)

    def test_operation_limit_is_atomic(self):
        snapshot = _snapshot()
        operation = operation_adapter.validate_python({"type": "add_rest", "duration_minutes": 10})
        result = apply_manual_operations(snapshot, [operation] * 21, catalog_spot_codes={"LS-01"})
        self.assertEqual(result.validation, "conflict")
        self.assertEqual(len(result.snapshot.stops), 1)
        self.assertEqual(result.diff, ())
