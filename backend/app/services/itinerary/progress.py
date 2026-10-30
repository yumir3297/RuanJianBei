from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.itinerary import StrictModel, TourSnapshotV2

StopProgress = Literal["pending", "current", "completed", "skipped"]
ProgressStatus = Literal["not_started", "active", "finished"]
ProgressEventType = Literal["started", "current_set", "completed", "skipped", "finished"]


class TourProgress(StrictModel):
    status: ProgressStatus = "not_started"
    started_at: datetime | None = None
    finish_by: datetime | None = None
    progress_version: int = Field(default=0, ge=0)
    current_stop_id: UUID | None = None
    status_by_stop: dict[str, StopProgress] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_current(self) -> TourProgress:
        current = [stop_id for stop_id, status in self.status_by_stop.items() if status == "current"]
        if len(current) > 1:
            raise ValueError("同时只能有一个当前停留点")
        if current and str(self.current_stop_id) != current[0]:
            raise ValueError("current_stop_id 与进度状态不一致")
        if not current and self.current_stop_id is not None:
            raise ValueError("没有 current 状态时 current_stop_id 必须为空")
        if self.status == "not_started" and (self.started_at is not None or self.finish_by is not None):
            raise ValueError("未开始的行程不能有开始时间或截止时间")
        if self.status != "not_started" and self.started_at is None:
            raise ValueError("已开始行程必须记录服务端开始时间")
        return self


class ProgressCommand(StrictModel):
    type: Literal["set_current", "complete", "skip", "finish"]
    stop_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target(self) -> ProgressCommand:
        if self.type == "finish" and self.stop_id is not None:
            raise ValueError("结束游览命令不接收停留点")
        if self.type != "finish" and self.stop_id is None:
            raise ValueError("进度命令需要 stop_id")
        return self


class ProgressEvent(StrictModel):
    version: int = Field(ge=1)
    event_type: ProgressEventType
    stop_id: UUID | None = None
    occurred_at: datetime


class ProgressTransition(StrictModel):
    progress: TourProgress
    event: ProgressEvent


class BudgetValidation(StrictModel):
    status: Literal["pass", "conflict", "unverified"]
    available_minutes: int | None = Field(default=None, ge=0)
    known_minutes: int = Field(default=0, ge=0)
    estimated_current_stop: bool = False
    unknown_stop_ids: list[UUID] = Field(default_factory=list)
    unknown_legs: list[tuple[UUID, UUID]] = Field(default_factory=list)
    message: str


class ProgressConflict(ValueError):
    pass


def _utc(now: datetime) -> datetime:
    return now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)


def start_tour(
    snapshot: TourSnapshotV2,
    *,
    plan_version: int,
    expected_plan_version: int,
    now: datetime,
) -> ProgressTransition:
    if plan_version != expected_plan_version:
        raise ProgressConflict("行程版本已变化，刷新后再开始游览")
    if not snapshot.stops:
        raise ProgressConflict("空行程不能开始游览")
    started_at = _utc(now)
    budget = snapshot.constraints.available_minutes
    finish_by = started_at + timedelta(minutes=budget) if budget is not None else None
    status_by_stop = {str(stop.stop_id): "pending" for stop in snapshot.stops}
    current_stop_id = snapshot.stops[0].stop_id
    status_by_stop[str(current_stop_id)] = "current"
    progress = TourProgress(
        status="active", started_at=started_at, finish_by=finish_by,
        progress_version=1, current_stop_id=current_stop_id, status_by_stop=status_by_stop,
    )
    return ProgressTransition(
        progress=progress,
        event=ProgressEvent(version=1, event_type="started", stop_id=current_stop_id, occurred_at=started_at),
    )


def apply_progress_command(
    progress: TourProgress,
    snapshot: TourSnapshotV2,
    *,
    expected_progress_version: int,
    command: ProgressCommand,
    now: datetime | None = None,
) -> ProgressTransition:
    if progress.status != "active":
        raise ProgressConflict("当前行程不在进行中")
    if expected_progress_version != progress.progress_version:
        raise ProgressConflict("游览进度已在其他位置更新")
    candidate = progress.model_copy(deep=True)
    order = [str(stop.stop_id) for stop in snapshot.stops]
    if set(order) != set(candidate.status_by_stop):
        raise ProgressConflict("行程条目与执行进度不匹配，不能覆盖已游事实")
    when = _utc(now or datetime.now(UTC))
    target = str(command.stop_id) if command.stop_id is not None else None
    event_type: ProgressEventType

    if command.type == "finish":
        if any(state in {"pending", "current"} for state in candidate.status_by_stop.values()):
            raise ProgressConflict("仍有未完成停留点；请逐项完成或跳过后再结束")
        candidate.status = "finished"
        candidate.current_stop_id = None
        event_type = "finished"
    else:
        if target not in candidate.status_by_stop:
            raise ProgressConflict("指定的停留点不属于当前行程")
        state = candidate.status_by_stop[target]
        if command.type == "set_current":
            pending = next((stop_id for stop_id in order if candidate.status_by_stop[stop_id] == "pending"), None)
            if state != "current" and (target != pending or candidate.current_stop_id is not None):
                raise ProgressConflict("只能将下一个待游览点设为当前点")
            if state == "pending":
                candidate.status_by_stop[target] = "current"
                candidate.current_stop_id = UUID(target)
            event_type = "current_set"
        elif command.type == "complete":
            if target != str(candidate.current_stop_id):
                raise ProgressConflict("只能完成当前停留点")
            candidate.status_by_stop[target] = "completed"
            candidate.current_stop_id = None
            event_type = "completed"
        else:  # skip current or a future pending stop; never alter historical states.
            if state not in {"current", "pending"}:
                raise ProgressConflict("已完成或已跳过的停留点不能再次跳过")
            current_index = order.index(str(candidate.current_stop_id)) if candidate.current_stop_id else -1
            if order.index(target) < current_index:
                raise ProgressConflict("不能跳过当前游览点之前的历史条目")
            candidate.status_by_stop[target] = "skipped"
            if target == str(candidate.current_stop_id):
                candidate.current_stop_id = None
            event_type = "skipped"

        if candidate.current_stop_id is None:
            next_pending = next((stop_id for stop_id in order if candidate.status_by_stop[stop_id] == "pending"), None)
            if next_pending is not None:
                candidate.status_by_stop[next_pending] = "current"
                candidate.current_stop_id = UUID(next_pending)
            elif all(state in {"completed", "skipped"} for state in candidate.status_by_stop.values()):
                candidate.status = "finished"

    candidate.progress_version += 1
    updated = TourProgress.model_validate(candidate.model_dump(mode="python"))
    return ProgressTransition(
        progress=updated,
        event=ProgressEvent(version=updated.progress_version, event_type=event_type,
                            stop_id=UUID(target) if target else None, occurred_at=when),
    )


def validate_remaining_budget(
    snapshot: TourSnapshotV2,
    progress: TourProgress | None,
    now: datetime,
    *,
    current_stop_remaining_minutes: int | None = None,
) -> BudgetValidation:
    when = _utc(now)
    if progress is None or progress.status == "not_started":
        remaining = list(snapshot.stops)
        available = snapshot.constraints.available_minutes
        current_id = None
    elif progress.status == "finished":
        return BudgetValidation(status="pass", available_minutes=0, known_minutes=0, message="游览已结束")
    else:
        available = None if progress.finish_by is None else max(0, int((progress.finish_by - when).total_seconds() // 60))
        remaining_ids = {stop_id for stop_id, state in progress.status_by_stop.items()
                         if state in {"current", "pending"}}
        remaining = [stop for stop in snapshot.stops if str(stop.stop_id) in remaining_ids]
        current_id = str(progress.current_stop_id) if progress.current_stop_id else None

    known = 0
    estimated_current_stop = False
    unknown_stop_ids: list[UUID] = []
    unknown_legs: list[tuple[UUID, UUID]] = []
    for stop in remaining:
        if str(stop.stop_id) == current_id:
            if current_stop_remaining_minutes is None:
                if stop.duration_minutes is None:
                    unknown_stop_ids.append(stop.stop_id)
                else:
                    known += stop.duration_minutes
                    estimated_current_stop = True
            elif current_stop_remaining_minutes < 0:
                raise ValueError("当前停留剩余分钟不能为负数")
            else:
                known += current_stop_remaining_minutes
        elif stop.duration_minutes is not None:
            known += stop.duration_minutes
        else:
            unknown_stop_ids.append(stop.stop_id)

    leg_by_pair = {(leg.from_stop_id, leg.to_stop_id): leg for leg in snapshot.legs}
    for left, right in zip(remaining, remaining[1:]):
        leg = leg_by_pair.get((left.stop_id, right.stop_id))
        if leg is None or leg.duration_minutes is None:
            unknown_legs.append((left.stop_id, right.stop_id))
        else:
            known += leg.duration_minutes

    if available is not None and known > available:
        status: Literal["pass", "conflict", "unverified"] = "conflict"
        message = "按当前点完整计划时长估算，已知剩余游览时长超过截止时间" if estimated_current_stop else "已知剩余游览时长超过截止时间"
    elif available is None or unknown_stop_ids or unknown_legs:
        status: Literal["pass", "conflict", "unverified"] = "unverified"
        message = "当前点按完整计划时长保守估算；剩余预算或部分停留/路段时长缺少可靠依据" if estimated_current_stop else "剩余预算或部分停留/路段时长缺少可靠依据"
    else:
        status = "pass"
        message = "按当前点完整计划时长保守估算，剩余游览时长在截止时间内" if estimated_current_stop else "已知剩余游览时长在截止时间内"
    return BudgetValidation(status=status, available_minutes=available, known_minutes=known,
                            estimated_current_stop=estimated_current_stop,
                            unknown_stop_ids=unknown_stop_ids, unknown_legs=unknown_legs, message=message)
