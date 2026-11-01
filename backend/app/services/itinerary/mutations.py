from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal, Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

from app.schemas.itinerary import (
    AddRest,
    AddVisit,
    ItineraryOperation,
    MoveStop,
    RemoveStop,
    ReplaceVisit,
    SetDuration,
    SetLock,
    ItineraryStop,
    TourSnapshotV2,
    UpdateConstraints,
)

Validation = Literal["pass", "conflict", "unverified"]
Actor = Literal["manual", "ai"]


@dataclass(frozen=True)
class ItineraryDiff:
    kind: Literal["added", "removed", "changed", "moved", "constraints", "legs", "source"]
    stop_id: str | None
    before: dict | None = None
    after: dict | None = None


@dataclass(frozen=True)
class MutationResult:
    snapshot: TourSnapshotV2
    diff: tuple[ItineraryDiff, ...]
    validation: Validation
    conflicts: tuple[str, ...]
    known_minutes: int


class _RejectedOperation(Exception):
    pass


def _lock(stop, field: str) -> bool:
    return "stop" in stop.locked_fields or field in stop.locked_fields


def _insert_position(stops, before_stop_id):
    if before_stop_id is None:
        return len(stops)
    for index, stop in enumerate(stops):
        if stop.stop_id == before_stop_id:
            return index
    raise _RejectedOperation("目标停留点不存在")


def _check_catalog(spot_code: str | None, catalog_spot_codes: set[str] | None) -> None:
    if spot_code and (catalog_spot_codes is None or spot_code not in catalog_spot_codes):
        raise _RejectedOperation("景点代码不在当前可用目录中")


def _apply(snapshot: TourSnapshotV2, operation: ItineraryOperation,
           catalog_spot_codes: set[str] | None, actor: Actor, created_stop_id: UUID) -> None:
    stops = snapshot.stops
    if isinstance(operation, AddVisit):
        _check_catalog(operation.spot_code, catalog_spot_codes)
        index = _insert_position(stops, operation.before_stop_id)
        stops.insert(index, ItineraryStop.model_validate({
            "stop_id": str(created_stop_id), "kind": "visit", "spot_code": operation.spot_code,
            "name": operation.name, "duration_minutes": operation.duration_minutes,
            "duration_basis": ("estimate" if actor == "ai" else "user") if operation.duration_minutes is not None else "unknown",
            "created_by": actor,
        }))
        return
    if isinstance(operation, AddRest):
        index = _insert_position(stops, operation.before_stop_id)
        stops.insert(index, ItineraryStop.model_validate({
            "stop_id": str(created_stop_id), "kind": "rest", "name": operation.name,
            "duration_minutes": operation.duration_minutes, "duration_basis": "estimate" if actor == "ai" else "user",
            "created_by": actor,
        }))
        return
    if isinstance(operation, UpdateConstraints):
        snapshot.constraints = operation.constraints
        return
    if isinstance(operation, (RemoveStop, ReplaceVisit, MoveStop, SetDuration, SetLock)):
        index = next((i for i, stop in enumerate(stops) if stop.stop_id == operation.stop_id), None)
        if index is None:
            raise _RejectedOperation("指定的停留点不存在")
        stop = stops[index]
        if isinstance(operation, SetLock):
            if actor != "manual":
                raise _RejectedOperation("AI 提案不能改变锁定状态")
            fields = set(stop.locked_fields)
            fields.add(operation.field) if operation.locked else fields.discard(operation.field)
            stop.locked_fields = sorted(fields)
            return
        if isinstance(operation, RemoveStop):
            if _lock(stop, "stop"):
                raise _RejectedOperation("停留点已锁定，不能删除")
            stops.pop(index)
            snapshot.legs = [leg for leg in snapshot.legs if leg.from_stop_id != stop.stop_id and leg.to_stop_id != stop.stop_id]
            return
        if isinstance(operation, ReplaceVisit):
            if stop.kind != "visit":
                raise _RejectedOperation("只能替换景点停留")
            if _lock(stop, "name") or _lock(stop, "spot_code"):
                raise _RejectedOperation("景点信息已锁定，不能替换")
            _check_catalog(operation.spot_code, catalog_spot_codes)
            stop.name = operation.name
            stop.spot_code = operation.spot_code
            stop.source_entry_id = None
            stop.source_revision_id = None
            stop.legacy_spot_id = None
            stop.legacy_content_version = None
            snapshot.legs = [leg for leg in snapshot.legs if leg.from_stop_id != stop.stop_id and leg.to_stop_id != stop.stop_id]
            stop.created_by = actor
            return
        if isinstance(operation, MoveStop):
            if _lock(stop, "position"):
                raise _RejectedOperation("停留点顺序已锁定，不能移动")
            moving = stops.pop(index)
            target_index = _insert_position(stops, operation.before_stop_id)
            stops.insert(target_index, moving)
            return
        if isinstance(operation, SetDuration):
            if _lock(stop, "duration"):
                raise _RejectedOperation("停留时长已锁定，不能修改")
            stop.duration_minutes = operation.duration_minutes
            stop.duration_basis = ("estimate" if actor == "ai" else "user") if operation.duration_minutes is not None else "unknown"
            stop.created_by = actor
            return
    raise _RejectedOperation("不支持的行程操作")


def _validate(snapshot: TourSnapshotV2) -> tuple[Validation, tuple[str, ...], int]:
    conflicts: list[str] = []
    required = set(snapshot.constraints.required_spots)
    excluded = set(snapshot.constraints.excluded_spots)
    if required & excluded:
        conflicts.append("同一景点不能同时设为必去和排除")
    actual = {stop.spot_code for stop in snapshot.stops if stop.kind == "visit" and stop.spot_code}
    if actual & excluded:
        conflicts.append("行程包含已排除景点")
    if required - actual:
        conflicts.append("行程缺少必去景点")

    known_minutes = sum(stop.duration_minutes or 0 for stop in snapshot.stops)
    leg_by_pair = {(leg.from_stop_id, leg.to_stop_id): leg for leg in snapshot.legs}
    unverified = bool(snapshot.constraints.available_minutes is None or
                      snapshot.constraints.unresolved_required_names or
                      snapshot.constraints.unresolved_excluded_names)
    for stop in snapshot.stops:
        if stop.duration_minutes is None or stop.duration_basis == "estimate" or (stop.kind == "visit" and stop.spot_code is None):
            unverified = True
    for left, right in zip(snapshot.stops, snapshot.stops[1:]):
        leg = leg_by_pair.get((left.stop_id, right.stop_id))
        if leg is None or leg.duration_minutes is None:
            unverified = True
        elif leg.duration_basis != "unknown":
            known_minutes += leg.duration_minutes
            if leg.duration_basis == "estimate":
                unverified = True

    budget = snapshot.constraints.available_minutes
    if budget is not None and known_minutes > budget:
        conflicts.append("计划停留与路段时长超过游览预算")
    if conflicts:
        return "conflict", tuple(conflicts), known_minutes
    if unverified:
        return "unverified", (), known_minutes
    return "pass", (), known_minutes


def diff_snapshots(before: TourSnapshotV2, after: TourSnapshotV2) -> tuple[ItineraryDiff, ...]:
    old = {stop.stop_id: stop for stop in before.stops}
    new = {stop.stop_id: stop for stop in after.stops}
    result: list[ItineraryDiff] = []
    for stop_id, stop in old.items():
        if stop_id not in new:
            result.append(ItineraryDiff("removed", str(stop_id), stop.model_dump(mode="json"), None))
    for stop_id, stop in new.items():
        if stop_id not in old:
            result.append(ItineraryDiff("added", str(stop_id), None, stop.model_dump(mode="json")))
        elif stop.model_dump(mode="json") != old[stop_id].model_dump(mode="json"):
            result.append(ItineraryDiff("changed", str(stop_id), old[stop_id].model_dump(mode="json"), stop.model_dump(mode="json")))
    before_order = [str(stop.stop_id) for stop in before.stops if stop.stop_id in new]
    after_order = [str(stop.stop_id) for stop in after.stops if stop.stop_id in old]
    if before_order != after_order:
        result.append(ItineraryDiff("moved", None, {"order": before_order}, {"order": after_order}))
    if before.constraints != after.constraints:
        result.append(ItineraryDiff(
            "constraints", None, before.constraints.model_dump(mode="json"), after.constraints.model_dump(mode="json"),
        ))
    before_legs = [leg.model_dump(mode="json") for leg in before.legs]
    after_legs = [leg.model_dump(mode="json") for leg in after.legs]
    if before_legs != after_legs:
        result.append(ItineraryDiff("legs", None, {"items": before_legs}, {"items": after_legs}))
    if before.source != after.source or before.source_references != after.source_references:
        result.append(ItineraryDiff(
            "source", None,
            {"source": before.source, "references": [item.model_dump(mode="json") for item in before.source_references]},
            {"source": after.source, "references": [item.model_dump(mode="json") for item in after.source_references]},
        ))
    return tuple(result)


def apply_manual_operations(
    snapshot: TourSnapshotV2,
    operations: Sequence[ItineraryOperation],
    *,
    catalog_spot_codes: set[str] | None,
    actor: Actor = "manual",
) -> MutationResult:
    """Apply allowlisted operations atomically; hard conflicts leave the input untouched."""
    original = snapshot.model_copy(deep=True)
    candidate = snapshot.model_copy(deep=True)
    if len(operations) > 20:
        return MutationResult(original, (), "conflict", ("单次最多允许 20 个行程操作",), 0)
    try:
        snapshot_fingerprint = candidate.model_dump_json()
        for index, operation in enumerate(operations):
            operation_fingerprint = json.dumps(operation.model_dump(mode="json"), ensure_ascii=False,
                                               sort_keys=True, separators=(",", ":"))
            created_stop_id = uuid5(NAMESPACE_URL, f"{snapshot_fingerprint}:{index}:{operation_fingerprint}")
            _apply(candidate, operation, catalog_spot_codes, actor, created_stop_id)
            # Re-validate after each operation so malformed intermediate state is never carried forward.
            candidate = TourSnapshotV2.model_validate(candidate.model_dump(mode="python"))
    except (ValueError, TypeError, _RejectedOperation) as error:
        message = str(error) or "行程操作无效"
        return MutationResult(original, (), "conflict", (message,), 0)
    validation, conflicts, known_minutes = _validate(candidate)
    if validation == "conflict":
        return MutationResult(original, (), validation, conflicts, known_minutes)
    return MutationResult(candidate, diff_snapshots(original, candidate), validation, (), known_minutes)
