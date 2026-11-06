from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from app.schemas.itinerary import (
    ItineraryOperation, MoveStop, RemoveStop, ReplaceVisit, SetDuration,
    SetLock, TourSnapshotV2, UpdateConstraints,
)
from app.services.itinerary.mutations import MutationResult, apply_manual_operations

MAX_PROPOSAL_CANDIDATES = 200


class CandidateSearchTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class CandidateSelection:
    operations: tuple[ItineraryOperation, ...]
    mutation: MutationResult
    candidate_count: int
    hard_conflicts: int
    unrelated_changes: int
    changed_stops: int
    preference_score: int

    def as_dict(self) -> dict:
        return {
            "candidate_count": self.candidate_count,
            "hard_conflicts": self.hard_conflicts,
            "unrelated_changes": self.unrelated_changes,
            "changed_stops": self.changed_stops,
            "preference_score": self.preference_score,
        }


def _operation_key(operation: ItineraryOperation) -> str:
    return json.dumps(operation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _required_fields(operations: Sequence[ItineraryOperation]) -> tuple[dict[str, set[str]], set[str], bool]:
    by_stop: dict[str, set[str]] = {}
    move_ids: set[str] = set()
    changes_constraints = False
    for operation in operations:
        stop_id = str(getattr(operation, "stop_id", ""))
        if isinstance(operation, SetDuration):
            by_stop.setdefault(stop_id, set()).update({"duration_minutes", "duration_basis", "created_by"})
        elif isinstance(operation, ReplaceVisit):
            by_stop.setdefault(stop_id, set()).update({
                "name", "spot_code", "source_entry_id", "source_revision_id",
                "legacy_spot_id", "legacy_content_version", "created_by",
            })
        elif isinstance(operation, MoveStop):
            move_ids.add(stop_id)
        elif isinstance(operation, (RemoveStop, SetLock)):
            by_stop.setdefault(stop_id, set()).add("__stop__")
        elif isinstance(operation, UpdateConstraints):
            changes_constraints = True
    return by_stop, move_ids, changes_constraints


def _order_changes_are_required(before: list[str], after: list[str], move_ids: set[str]) -> bool:
    shared = set(before) & set(after)
    old = [stop_id for stop_id in before if stop_id in shared]
    new = [stop_id for stop_id in after if stop_id in shared]
    if old == new:
        return True
    positions = {stop_id: index for index, stop_id in enumerate(new)}
    inverted = set()
    for index, left in enumerate(old):
        for right in old[index + 1:]:
            if positions[left] > positions[right]:
                inverted.update((left, right))
    return bool(move_ids) and inverted.issubset(move_ids)


def _moved_stop_count(before: list[str], after: list[str]) -> int:
    shared = set(before) & set(after)
    old = [stop_id for stop_id in before if stop_id in shared]
    new = [stop_id for stop_id in after if stop_id in shared]
    if old == new:
        return 0
    old_pos = {stop_id: index for index, stop_id in enumerate(old)}
    new_pos = {stop_id: index for index, stop_id in enumerate(new)}
    return len({stop_id for stop_id in shared if old_pos[stop_id] != new_pos[stop_id]})


def _score_changes(snapshot: TourSnapshotV2, result: MutationResult,
                   required_operations: Sequence[ItineraryOperation]) -> tuple[int, int, int]:
    if result.validation == "conflict":
        return len(result.conflicts), len(required_operations), 0
    before = {str(stop.stop_id): stop.model_dump(mode="json") for stop in snapshot.stops}
    after = {str(stop.stop_id): stop.model_dump(mode="json") for stop in result.snapshot.stops}
    required_fields, move_ids, constraints_required = _required_fields(required_operations)
    unrelated = 0
    changed_ids: set[str] = set()
    for stop_id in before.keys() | after.keys():
        old, new = before.get(stop_id), after.get(stop_id)
        if old is None or new is None:
            changed_ids.add(stop_id)
            if stop_id not in required_fields:
                unrelated += 1
            continue
        changed_fields = {key for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
        if changed_fields:
            changed_ids.add(stop_id)
        allowed = required_fields.get(stop_id, set())
        unrelated += sum(1 for key in changed_fields if key not in allowed)

    before_order = [str(stop.stop_id) for stop in snapshot.stops]
    after_order = [str(stop.stop_id) for stop in result.snapshot.stops]
    if not _order_changes_are_required(before_order, after_order, move_ids):
        unrelated += 1
    if snapshot.constraints != result.snapshot.constraints and not constraints_required:
        unrelated += 1

    old_legs = {(str(leg.from_stop_id), str(leg.to_stop_id)): leg.model_dump(mode="json") for leg in snapshot.legs}
    new_legs = {(str(leg.from_stop_id), str(leg.to_stop_id)): leg.model_dump(mode="json") for leg in result.snapshot.legs}
    if old_legs != new_legs:
        operation_targets = set(required_fields)
        changed_leg_pairs = old_legs.keys() ^ new_legs.keys()
        changed_leg_pairs |= {pair for pair in old_legs.keys() & new_legs.keys() if old_legs[pair] != new_legs[pair]}
        if any(not (set(pair) & operation_targets) for pair in changed_leg_pairs):
            unrelated += 1
    changed_stops = len(changed_ids) + _moved_stop_count(before_order, after_order)
    return len(result.conflicts), unrelated, changed_stops


def _has_less_walking_preference(snapshot: TourSnapshotV2) -> bool:
    words = " ".join([snapshot.constraints.walking_preference or "", *snapshot.constraints.interests]).casefold()
    return "少走" in words or "less walking" in words or "less_walking" in words


def select_candidate(
    snapshot: TourSnapshotV2,
    alternatives: Sequence[Sequence[ItineraryOperation]],
    *,
    required_operations: Sequence[ItineraryOperation],
    catalog_spot_codes: set[str],
    prefer_less_walking: bool = False,
    max_candidates: int = MAX_PROPOSAL_CANDIDATES,
) -> CandidateSelection:
    """Run each complete candidate through the shared reducer and select deterministically.

    Preference scoring only uses an explicit less-walking request as an approximate
    stop-count signal. It never claims to know actual route distance.
    """
    if not alternatives:
        raise ValueError("没有可验证的修改候选")

    unique: dict[str, tuple[ItineraryOperation, ...]] = {}
    for operations in alternatives:
        frozen = tuple(operations)
        signature = json.dumps([json.loads(_operation_key(op)) for op in frozen], ensure_ascii=False,
                               sort_keys=True, separators=(",", ":"))
        unique.setdefault(signature, frozen)
    if len(unique) > max_candidates:
        raise CandidateSearchTooLarge("可选方案过多，请缩小修改范围或手动调整行程")

    scored: list[tuple[tuple, CandidateSelection]] = []
    less_walking = prefer_less_walking or _has_less_walking_preference(snapshot)
    for signature, operations in sorted(unique.items()):
        required = Counter(_operation_key(op) for op in required_operations)
        actual = Counter(_operation_key(op) for op in operations)
        missing_required = sum((required - actual).values())
        extra_operations = sum((actual - required).values())
        mutation = apply_manual_operations(snapshot, operations, catalog_spot_codes=catalog_spot_codes, actor="ai")
        hard_conflicts, unrelated_changes, changed_stops = _score_changes(snapshot, mutation, required_operations)
        if missing_required:
            hard_conflicts += missing_required
        unrelated_changes = max(unrelated_changes, extra_operations)
        preference_score = -sum(stop.kind == "visit" for stop in mutation.snapshot.stops) if less_walking and mutation.validation != "conflict" else 0
        validation_penalty = 0 if mutation.validation == "pass" else 1
        choice = CandidateSelection(operations, mutation, len(unique), hard_conflicts,
                                    unrelated_changes, changed_stops, preference_score)
        score = (hard_conflicts, unrelated_changes, changed_stops, validation_penalty,
                 -preference_score, signature)
        scored.append((score, choice))
    return min(scored, key=lambda item: item[0])[1]
