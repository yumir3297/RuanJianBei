import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.schemas.itinerary import TourSnapshotV2
from app.services.itinerary.progress import (
    ProgressConflict,
    ProgressCommand,
    TourProgress,
    apply_progress_command,
    start_tour,
    validate_remaining_budget,
)


def _snapshot():
    first, second = str(uuid4()), str(uuid4())
    return TourSnapshotV2.model_validate({
        "schema_version": 2,
        "constraints": {"available_minutes": 60},
        "stops": [
            {"stop_id": first, "kind": "visit", "spot_code": "LS-01", "name": "梵宫",
             "duration_minutes": 20, "duration_basis": "user"},
            {"stop_id": second, "kind": "rest", "name": "休息", "duration_minutes": 10,
             "duration_basis": "user"},
        ],
    })


class ItineraryProgressTests(unittest.TestCase):
    def test_start_stores_server_time_and_deadline(self):
        snapshot = _snapshot()
        now = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
        result = start_tour(snapshot, plan_version=4, expected_plan_version=4, now=now)
        self.assertEqual(result.progress.started_at, now)
        self.assertEqual(result.progress.finish_by, now + timedelta(minutes=60))
        self.assertEqual(result.progress.progress_version, 1)
        self.assertEqual(result.progress.status_by_stop[str(snapshot.stops[0].stop_id)], "current")

    def test_stale_plan_version_cannot_start(self):
        with self.assertRaises(ProgressConflict):
            start_tour(_snapshot(), plan_version=5, expected_plan_version=4,
                       now=datetime.now(UTC))

    def test_complete_advances_without_mutating_plan(self):
        snapshot = _snapshot()
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))
        first_id, second_id = [str(stop.stop_id) for stop in snapshot.stops]
        result = apply_progress_command(started.progress, snapshot, expected_progress_version=1,
                                        command=ProgressCommand(type="complete", stop_id=first_id))
        self.assertEqual(result.progress.status_by_stop[first_id], "completed")
        self.assertEqual(result.progress.status_by_stop[second_id], "current")
        self.assertEqual(str(result.progress.current_stop_id), second_id)
        self.assertEqual(len(snapshot.stops), 2)

    def test_future_skip_is_preserved_when_current_stop_completes(self):
        snapshot = _snapshot()
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))
        first_id, second_id = [str(stop.stop_id) for stop in snapshot.stops]
        skipped = apply_progress_command(started.progress, snapshot, expected_progress_version=1,
                                         command=ProgressCommand(type="skip", stop_id=second_id))
        done = apply_progress_command(skipped.progress, snapshot, expected_progress_version=2,
                                      command=ProgressCommand(type="complete", stop_id=first_id))
        self.assertEqual(done.progress.status_by_stop[second_id], "skipped")
        self.assertEqual(done.progress.status, "finished")

    def test_deadline_checks_only_pending_plan_and_unknown_remains_unverified(self):
        snapshot_data = _snapshot().model_dump(mode="json")
        snapshot_data["stops"].append({
            "stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-02", "name": "五印坛城",
            "duration_minutes": 15, "duration_basis": "user",
        })
        snapshot = TourSnapshotV2.model_validate(snapshot_data)
        now = datetime(2026, 10, 29, 8, 20, tzinfo=UTC)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=now)
        first_id = str(snapshot.stops[0].stop_id)
        current = apply_progress_command(started.progress, snapshot, expected_progress_version=1,
                                         command=ProgressCommand(type="complete", stop_id=first_id)).progress
        budget = validate_remaining_budget(snapshot, current, now + timedelta(minutes=10))
        self.assertEqual(budget.available_minutes, 50)
        self.assertEqual(budget.known_minutes, 25)
        self.assertTrue(budget.estimated_current_stop)
        self.assertEqual(budget.status, "unverified")  # the remaining route leg has no reliable duration

    def test_stale_progress_version_is_rejected(self):
        snapshot = _snapshot()
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))
        with self.assertRaises(ProgressConflict):
            apply_progress_command(started.progress, snapshot, expected_progress_version=0,
                                   command=ProgressCommand(type="skip", stop_id=str(snapshot.stops[1].stop_id)))

    def test_known_overrun_is_conflict_even_when_a_road_leg_is_unknown(self):
        snapshot_data = _snapshot().model_dump(mode="json")
        snapshot_data["stops"].append({
            "stop_id": str(uuid4()), "kind": "visit", "spot_code": "LS-02", "name": "五印坛城",
            "duration_minutes": 45, "duration_basis": "user",
        })
        snapshot = TourSnapshotV2.model_validate(snapshot_data)
        now = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=now)
        result = validate_remaining_budget(snapshot, started.progress, now + timedelta(minutes=35))
        self.assertEqual(result.available_minutes, 25)
        self.assertEqual(result.known_minutes, 75)
        self.assertEqual(result.status, "conflict")

    def test_current_stop_uses_conservative_plan_duration_at_exact_budget_boundary(self):
        data = _snapshot().model_dump(mode="json")
        data["stops"] = data["stops"][:1]
        snapshot = TourSnapshotV2.model_validate(data)
        now = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=now)

        result = validate_remaining_budget(snapshot, started.progress, now + timedelta(minutes=40))

        self.assertEqual(result.available_minutes, 20)
        self.assertEqual(result.known_minutes, 20)
        self.assertTrue(result.estimated_current_stop)
        self.assertEqual(result.status, "pass")

    def test_explicit_current_stop_remaining_time_overrides_plan_estimate(self):
        data = _snapshot().model_dump(mode="json")
        data["stops"] = data["stops"][:1]
        snapshot = TourSnapshotV2.model_validate(data)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))

        result = validate_remaining_budget(snapshot, started.progress, datetime.now(UTC),
            current_stop_remaining_minutes=5)

        self.assertEqual(result.known_minutes, 5)
        self.assertFalse(result.estimated_current_stop)

    def test_past_deadline_conflicts_even_if_current_remaining_is_zero(self):
        data = _snapshot().model_dump(mode="json")
        data["stops"] = data["stops"][:1]
        snapshot = TourSnapshotV2.model_validate(data)
        now = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=now)

        result = validate_remaining_budget(snapshot, started.progress, now + timedelta(minutes=61),
            current_stop_remaining_minutes=0)

        self.assertEqual(result.available_minutes, 0)
        self.assertEqual(result.known_minutes, 0)
        self.assertEqual(result.status, "conflict")
        self.assertIn("已超过截止时间", result.message)

    def test_current_stop_without_plan_duration_remains_unverified(self):
        data = _snapshot().model_dump(mode="json")
        data["stops"] = data["stops"][:1]
        data["stops"][0]["duration_minutes"] = None
        data["stops"][0]["duration_basis"] = "unknown"
        snapshot = TourSnapshotV2.model_validate(data)
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))

        result = validate_remaining_budget(snapshot, started.progress, datetime.now(UTC))

        self.assertEqual(result.status, "unverified")
        self.assertEqual(result.known_minutes, 0)
        self.assertFalse(result.estimated_current_stop)
        self.assertEqual([str(stop_id) for stop_id in result.unknown_stop_ids],
            [str(snapshot.stops[0].stop_id)])

    def test_unknown_stop_duration_is_reported_as_unverified_not_zero(self):
        data = _snapshot().model_dump(mode="json")
        unknown_id = str(uuid4())
        data["stops"].append({
            "stop_id": unknown_id, "kind": "visit", "spot_code": "LS-02", "name": "五印坛城",
            "duration_minutes": None, "duration_basis": "unknown",
        })
        snapshot = TourSnapshotV2.model_validate(data)

        result = validate_remaining_budget(snapshot, None, datetime(2026, 10, 29, 8, 0, tzinfo=UTC))

        self.assertEqual(result.status, "unverified")
        self.assertEqual(result.known_minutes, 30)
        self.assertEqual([str(stop_id) for stop_id in result.unknown_stop_ids], [unknown_id])

    def test_missing_total_budget_stays_unverified_even_for_a_single_known_stop(self):
        data = _snapshot().model_dump(mode="json")
        data["constraints"]["available_minutes"] = None
        data["stops"] = data["stops"][:1]
        snapshot = TourSnapshotV2.model_validate(data)

        result = validate_remaining_budget(snapshot, None, datetime(2026, 10, 29, 8, 0, tzinfo=UTC))

        self.assertEqual(result.status, "unverified")
        self.assertIsNone(result.available_minutes)
        self.assertEqual(result.known_minutes, 20)

    def test_finished_tour_has_no_remaining_budget(self):
        snapshot = _snapshot()
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))
        first_id, second_id = [str(stop.stop_id) for stop in snapshot.stops]
        first_done = apply_progress_command(started.progress, snapshot, expected_progress_version=1,
            command=ProgressCommand(type="complete", stop_id=first_id))
        finished = apply_progress_command(first_done.progress, snapshot, expected_progress_version=2,
            command=ProgressCommand(type="complete", stop_id=second_id))

        result = validate_remaining_budget(snapshot, finished.progress, datetime.now(UTC))

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.available_minutes, 0)
        self.assertEqual(result.known_minutes, 0)

    def test_negative_current_stop_remaining_time_is_rejected(self):
        snapshot = _snapshot()
        started = start_tour(snapshot, plan_version=1, expected_plan_version=1, now=datetime.now(UTC))

        with self.assertRaisesRegex(ValueError, "不能为负数"):
            validate_remaining_budget(snapshot, started.progress, datetime.now(UTC),
                current_stop_remaining_minutes=-1)
