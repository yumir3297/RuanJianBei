from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tour_session import TourProgressRecord, TourSession
from app.models.tool_execution import ToolAttempt, ToolCommandReceipt, ToolEvent, ToolJob, ToolStep

MAX_INPUT_BYTES = 1024 * 1024
MAX_STEP_RESULT_BYTES = 1024 * 1024
MAX_JOB_RESULT_BYTES = 4 * 1024 * 1024
MAX_EVENT_PAYLOAD_BYTES = 8 * 1024
MAX_STEPS_PER_JOB = 100
MAX_EVENT_PAGE = 100
RECEIPT_TTL = timedelta(days=7)
ACTIVE_STATES = ("queued", "retry_wait", "running", "waiting_user")


class IdempotencyConflict(Exception):
    pass


class LeaseLost(Exception):
    pass


class JobCommandError(Exception):
    pass


@dataclass(frozen=True)
class JobLease:
    job_id: str
    worker_id: str
    fence: int
    principal_type: str
    principal_id: str
    site_id: str
    target_type: str
    target_id: str
    base_revision: int
    progress_version: int | None
    content_digest: str | None
    tool_name: str
    tool_version: str
    workflow_schema_version: str
    input_payload: dict[str, Any]
    deadline_at: datetime


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _decode(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {} if fallback is None else fallback


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _size(value: Any) -> int:
    return len(_json(value).encode("utf-8"))


class ToolExecutionRepository:
    """Transactional W02 state transitions. Provider work never runs in these transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _target_current_clause(self):
        session_is_current = exists(select(1).select_from(TourSession).where(
            TourSession.id == ToolJob.target_id,
            TourSession.owner_id == ToolJob.principal_id,
            TourSession.site_id == ToolJob.site_id,
            TourSession.version == ToolJob.base_revision,
            TourSession.deleted_at.is_(None),
        )).correlate(ToolJob)
        has_progress = exists(select(1).select_from(TourProgressRecord).where(
            TourProgressRecord.session_id == ToolJob.target_id,
        )).correlate(ToolJob)
        progress_is_current = or_(
            ToolJob.progress_version.is_(None),
            exists(select(1).select_from(TourProgressRecord).where(
                TourProgressRecord.session_id == ToolJob.target_id,
                TourProgressRecord.progress_version == ToolJob.progress_version,
            )).correlate(ToolJob),
            and_(ToolJob.progress_version == 0, ~has_progress),
        )
        return and_(session_is_current, progress_is_current)

    async def _lock_current_target(self, job_id: str) -> bool:
        query = select(TourSession.id).join(
            ToolJob, ToolJob.target_id == TourSession.id,
        ).where(
            ToolJob.id == job_id, ToolJob.target_type == "tour_session",
            ToolJob.principal_type == "tourist",
            TourSession.owner_id == ToolJob.principal_id,
            TourSession.site_id == ToolJob.site_id,
            TourSession.version == ToolJob.base_revision,
            TourSession.deleted_at.is_(None),
            self._target_current_clause(),
        )
        if self.session.get_bind().dialect.name == "postgresql":
            query = query.with_for_update(of=TourSession)
        return await self.session.scalar(query) is not None

    async def _event(
        self, job_id: str, event_type: str, summary: str, payload: dict[str, Any] | None = None,
    ) -> None:
        safe_payload = payload or {}
        if _size(safe_payload) > MAX_EVENT_PAYLOAD_BYTES:
            safe_payload = {"truncated": True}
        seq = int(await self.session.scalar(select(func.coalesce(func.max(ToolEvent.seq), 0)).where(
            ToolEvent.job_id == job_id,
        )) or 0) + 1
        self.session.add(ToolEvent(
            id=str(uuid4()), job_id=job_id, seq=seq, event_type=event_type,
            summary=summary[:240], payload_json=_json(safe_payload), created_at=datetime.now(UTC),
        ))
        await self.session.flush()

    async def _close_steps(
        self, job_id: str, status: str, reason: str, now: datetime,
    ) -> bool:
        steps = (await self.session.scalars(select(ToolStep).where(
            ToolStep.job_id == job_id, ToolStep.status.in_(ACTIVE_STATES),
        ))).all()
        any_uncertain = False
        for step in steps:
            uncertain = step.external_state in ("may_have_run", "unknown")
            any_uncertain = any_uncertain or uncertain
            step.status = status
            step.error_code = "external_outcome_unknown" if uncertain else reason[:80]
            if uncertain:
                step.external_state = "unknown"
            step.completed_at = now
            step.updated_at = now
            if step.attempt_count:
                attempt = await self.session.scalar(select(ToolAttempt).where(
                    ToolAttempt.step_id == step.id,
                    ToolAttempt.attempt_number == step.attempt_count,
                ))
                if attempt and attempt.finished_at is None:
                    attempt.finished_at = now
                    attempt.outcome = "unknown" if uncertain else status
                    attempt.error_code = "external_outcome_unknown" if uncertain else reason[:80]
        return any_uncertain

    async def _view(self, job: ToolJob, *, include_steps: bool = True) -> dict[str, Any]:
        latest_seq = int(await self.session.scalar(select(func.coalesce(func.max(ToolEvent.seq), 0)).where(
            ToolEvent.job_id == job.id,
        )) or 0)
        steps: list[dict[str, Any]] = []
        if include_steps:
            rows = (await self.session.scalars(select(ToolStep).where(
                ToolStep.job_id == job.id,
            ).order_by(ToolStep.created_at, ToolStep.step_key))).all()
            steps = [{
                "key": row.step_key, "status": row.status, "attempt_count": row.attempt_count,
                "max_attempts": row.max_attempts, "error_code": row.error_code,
                "result": _decode(row.result_json) if row.result_json else None,
            } for row in rows]
        return {
            "id": job.id, "site_id": job.site_id, "target_type": job.target_type,
            "target_id": job.target_id, "tool_name": job.tool_name, "tool_version": job.tool_version,
            "workflow_schema_version": job.workflow_schema_version,
            "recovery_mode": job.recovery_mode, "retry_safe": job.retry_safe,
            "input_digest": job.input_digest,
            "base_revision": job.base_revision, "progress_version": job.progress_version,
            "content_digest": job.content_digest, "status": job.status, "reason": job.reason,
            "progress": _decode(job.progress_json),
            "result": _decode(job.result_json) if job.result_json else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "event_seq": latest_seq, "steps": steps,
        }

    async def _receipt(
        self, principal_type: str, principal_id: str, command: str, key: str, payload_digest: str,
    ) -> ToolCommandReceipt | None:
        if not key or len(key) > 128:
            raise ValueError("幂等键长度必须为 1 到 128 个字符")
        receipt = await self.session.scalar(select(ToolCommandReceipt).where(
            ToolCommandReceipt.principal_type == principal_type,
            ToolCommandReceipt.principal_id == principal_id,
            ToolCommandReceipt.command == command,
            ToolCommandReceipt.key == key,
        ))
        if receipt is None:
            return None
        if _aware(receipt.expires_at) <= datetime.now(UTC):
            await self.session.delete(receipt)
            await self.session.flush()
            return None
        if receipt.payload_digest != payload_digest:
            raise IdempotencyConflict("幂等键已用于不同内容")
        return receipt

    async def _replay_view(self, receipt: ToolCommandReceipt | None) -> dict[str, Any] | None:
        if receipt is None or receipt.job_id is None:
            return None
        job = await self.session.get(ToolJob, receipt.job_id)
        return await self._view(job) if job else None

    async def create_job(
        self,
        *,
        principal_type: str,
        principal_id: str,
        site_id: str,
        tool_name: str,
        tool_version: str,
        workflow_schema_version: str,
        recovery_mode: str,
        retry_safe: bool,
        target: dict[str, Any],
        payload: dict[str, Any],
        idempotency_key: str,
        deadline_seconds: int = 3600,
        max_attempts: int = 3,
        commit: bool = True,
    ) -> dict[str, Any]:
        if principal_type != "tourist":
            raise ValueError("当前执行内核只接受已认证的游客主体")
        if target.get("type") != "tour_session":
            raise ValueError("当前只支持绑定游览任务的执行")
        if recovery_mode not in ("query_only", "manual_retry", "durable_resume"):
            raise ValueError("未知的任务恢复策略")
        if not 1 <= deadline_seconds <= 24 * 60 * 60:
            raise ValueError("任务时限超出允许范围")
        if not 1 <= max_attempts <= 3:
            raise ValueError("自动尝试次数超出允许范围")
        if not isinstance(retry_safe, bool) or (not retry_safe and max_attempts != 1):
            raise ValueError("未声明安全重试的工具只能运行一次")
        if _size(payload) > MAX_INPUT_BYTES:
            raise ValueError("任务输入超过 1 MiB 限制")
        request = {
            "site_id": site_id, "tool_name": tool_name, "tool_version": tool_version,
            "workflow_schema_version": workflow_schema_version, "recovery_mode": recovery_mode,
            "retry_safe": retry_safe,
            "target": target, "payload": payload, "deadline_seconds": deadline_seconds,
            "max_attempts": max_attempts,
        }
        payload_digest = _digest(request)
        replay = await self._receipt(principal_type, principal_id, "create", idempotency_key, payload_digest)
        if replay:
            result = await self._replay_view(replay)
            if result:
                return result

        target_id = str(target.get("id", ""))
        base_revision = int(target.get("base_revision", 0))
        target_query = select(TourSession).where(
            TourSession.id == target_id, TourSession.owner_id == principal_id,
            TourSession.site_id == site_id, TourSession.version == base_revision,
            TourSession.deleted_at.is_(None),
        )
        if self.session.get_bind().dialect.name == "postgresql":
            target_query = target_query.with_for_update()
        session = await self.session.scalar(target_query)
        if session is None:
            raise JobCommandError("游览不存在、已删除或已更新")
        progress_version = target.get("progress_version")
        if progress_version is not None:
            actual_progress_version = await self.session.scalar(select(TourProgressRecord.progress_version).where(
                TourProgressRecord.session_id == target_id,
            ))
            if (actual_progress_version or 0) != progress_version:
                raise JobCommandError("游览进度已更新")
        now = datetime.now(UTC)
        job_id = str(uuid4())
        step_id = str(uuid4())
        job = ToolJob(
            id=job_id, principal_type=principal_type, principal_id=principal_id, site_id=site_id,
            target_type="tour_session", target_id=target_id, tool_name=tool_name,
            tool_version=tool_version, workflow_schema_version=workflow_schema_version,
            recovery_mode=recovery_mode,
            retry_safe=retry_safe,
            input_json=_json(payload), input_digest=_digest(payload), base_revision=base_revision,
            progress_version=progress_version, content_digest=target.get("content_digest"),
            status="queued", reason=None, progress_json="{}", result_json=None,
            next_run_at=now, deadline_at=now + timedelta(seconds=deadline_seconds),
            fence=0, manual_retry_count=0, created_at=now, updated_at=now,
        )
        step_input = {"tool_name": tool_name, "input_digest": job.input_digest}
        step = ToolStep(
            id=step_id, job_id=job_id, step_key="run", status="queued",
            input_digest=_digest(step_input), result_json=None, attempt_count=0,
            max_attempts=max_attempts, external_state="not_started", created_at=now, updated_at=now,
        )
        receipt = ToolCommandReceipt(
            id=str(uuid4()), principal_type=principal_type, principal_id=principal_id,
            command="create", key=idempotency_key, payload_digest=payload_digest,
            job_id=job_id, response_json=_json({"job_id": job_id}),
            expires_at=now + RECEIPT_TTL, created_at=now,
        )
        try:
            # Explicitly flush the parent before dependent rows: without ORM
            # relationships SQLAlchemy may insert the receipt first, which
            # PostgreSQL rejects under its immediate foreign-key constraint.
            self.session.add(job)
            await self.session.flush()
            self.session.add_all([step, receipt])
            await self._event(job_id, "queued", "任务已进入执行队列")
            if commit:
                await self.session.commit()
            else:
                await self.session.flush()
        except IntegrityError:
            if commit:
                await self.session.rollback()
                receipt = await self._receipt(principal_type, principal_id, "create", idempotency_key, payload_digest)
                replay_result = await self._replay_view(receipt)
                if replay_result:
                    return replay_result
            raise
        if commit:
            return await self.get_job(principal_type, principal_id, site_id, target_id, job_id) or {}
        return await self._view(job)

    async def _expire_deadlines(self, now: datetime) -> int:
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.status.in_(("queued", "retry_wait", "running")),
            ToolJob.deadline_at <= now,
        ).limit(200))).all()
        changed = 0
        for job in jobs:
            step = await self.session.scalar(select(ToolStep).where(
                ToolStep.job_id == job.id, ToolStep.status.in_(("running", "queued", "retry_wait")),
            ))
            uncertain = bool(step and step.status == "running" and step.external_state == "may_have_run")
            new_status = "waiting_user" if uncertain else "failed"
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status == job.status,
                ToolJob.fence == job.fence,
            ).values(
                status=new_status, reason="external_outcome_unknown" if uncertain else "job_timeout",
                lease_owner=None, lease_until=None, fence=ToolJob.fence + 1,
                completed_at=None if uncertain else now, updated_at=now,
            ).execution_options(synchronize_session=False))
            if result.rowcount != 1:
                continue
            if step:
                step.status = "waiting_user" if uncertain else "failed"
                if uncertain:
                    step.external_state = "unknown"
                step.error_code = "external_outcome_unknown" if uncertain else "job_timeout"
                step.updated_at = now
                attempt = await self.session.scalar(select(ToolAttempt).where(
                    ToolAttempt.step_id == step.id,
                    ToolAttempt.attempt_number == step.attempt_count,
                )) if step.attempt_count else None
                if attempt and attempt.finished_at is None:
                    attempt.finished_at = now
                    attempt.outcome = "unknown" if uncertain else "failed"
                    attempt.error_code = step.error_code
            await self._event(job.id, new_status, "任务超过截止时间", {"reason": "job_timeout"})
            changed += 1
        return changed

    async def _stale_incompatible_targets(self, now: datetime, limit: int = 200) -> int:
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.status.in_(ACTIVE_STATES),
            ~self._target_current_clause(),
        ).limit(limit))).all()
        changed = 0
        for job in jobs:
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status == job.status, ToolJob.fence == job.fence,
            ).values(status="stale", reason="target_revision_changed", lease_owner=None,
                     lease_until=None, fence=ToolJob.fence + 1, completed_at=now, updated_at=now)
             .execution_options(synchronize_session=False))
            if result.rowcount == 1:
                uncertain = await self._close_steps(job.id, "stale", "target_revision_changed", now)
                await self._event(job.id, "stale", "游览内容已更新，任务结果需要复核", {
                    "external_outcome_unknown": uncertain,
                })
                changed += 1
        return changed

    async def _recover_expired_leases(self, now: datetime, limit: int = 100) -> int:
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.status == "running",
            (ToolJob.lease_until <= now) | ToolJob.lease_until.is_(None),
        ).order_by(ToolJob.lease_until).limit(limit))).all()
        changed = 0
        for job in jobs:
            step = await self.session.scalar(select(ToolStep).where(
                ToolStep.job_id == job.id, ToolStep.status == "running",
            ))
            uncertain = bool(step and step.external_state == "may_have_run")
            status = "waiting_user" if uncertain else "queued"
            values: dict[str, Any] = {
                "status": status, "reason": "external_outcome_unknown" if uncertain else "lease_expired",
                "lease_owner": None, "lease_until": None, "fence": ToolJob.fence + 1,
                "updated_at": now,
            }
            if not uncertain:
                values.update(next_run_at=now, completed_at=None)
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status == "running", ToolJob.fence == job.fence,
                (ToolJob.lease_until <= now) | ToolJob.lease_until.is_(None),
            ).values(**values).execution_options(synchronize_session=False))
            if result.rowcount != 1:
                continue
            if step:
                step.status = "waiting_user" if uncertain else "queued"
                step.updated_at = now
                if uncertain:
                    step.external_state = "unknown"
                    step.error_code = "external_outcome_unknown"
                attempt = await self.session.scalar(select(ToolAttempt).where(
                    ToolAttempt.step_id == step.id,
                    ToolAttempt.attempt_number == step.attempt_count,
                ))
                if attempt and attempt.finished_at is None:
                    attempt.finished_at = now
                    attempt.outcome = "unknown" if uncertain else "interrupted"
                    attempt.error_code = "external_outcome_unknown" if uncertain else "lease_expired"
            await self._event(
                job.id, status,
                "外部调用结果不确定，需要确认" if uncertain else "工作进程中断，安全步骤已重新排队",
                {"reason": values["reason"]},
            )
            changed += 1
        return changed

    async def maintain(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        changed = {
            "expired": await self._expire_deadlines(now),
            "stale": await self._stale_incompatible_targets(now),
            "recovered": await self._recover_expired_leases(now),
        }
        await self.session.execute(delete(ToolCommandReceipt).where(ToolCommandReceipt.expires_at <= now))
        await self.session.commit()
        return changed

    async def claim_next(self, worker_id: str, lease_seconds: int = 30, now: datetime | None = None) -> JobLease | None:
        if not worker_id or len(worker_id) > 100:
            raise ValueError("worker_id 长度必须为 1 到 100 个字符")
        now = now or datetime.now(UTC)
        # SQLite serializes a conditional UPDATE; PostgreSQL additionally skips rows held by other workers.
        candidates = select(ToolJob).where(
            ToolJob.status.in_(("queued", "retry_wait")), ToolJob.next_run_at <= now,
            ToolJob.deadline_at > now, self._target_current_clause(),
        ).order_by(ToolJob.next_run_at, ToolJob.created_at).limit(1)
        if self.session.get_bind().dialect.name == "postgresql":
            candidates = candidates.with_for_update(skip_locked=True)
        try:
            job = await self.session.scalar(candidates)
            if job is None:
                await self.session.rollback()
                return None
            prior_status = job.status
            prior_fence = job.fence
            until = now + timedelta(seconds=max(5, min(lease_seconds, 300)))
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status == prior_status, ToolJob.fence == prior_fence,
                ToolJob.next_run_at <= now, ToolJob.deadline_at > now, self._target_current_clause(),
            ).values(status="running", lease_owner=worker_id, lease_until=until,
                     fence=ToolJob.fence + 1, reason=None, updated_at=now)
             .execution_options(synchronize_session=False))
            if result.rowcount != 1:
                await self.session.rollback()
                return None
            fence = prior_fence + 1
            step = await self.session.scalar(select(ToolStep).where(
                ToolStep.job_id == job.id, ToolStep.step_key == "run",
            ))
            if step and step.status in ("queued", "retry_wait"):
                step.status = "running"
                step.updated_at = now
            await self._event(job.id, "running", "工作进程已领取任务")
            await self.session.commit()
            return JobLease(
                job_id=job.id, worker_id=worker_id, fence=fence,
                principal_type=job.principal_type, principal_id=job.principal_id, site_id=job.site_id,
                target_type=job.target_type, target_id=job.target_id, base_revision=job.base_revision,
                progress_version=job.progress_version, content_digest=job.content_digest,
                tool_name=job.tool_name, tool_version=job.tool_version,
                workflow_schema_version=job.workflow_schema_version,
                input_payload=_decode(job.input_json, {}), deadline_at=job.deadline_at,
            )
        except OperationalError as error:
            await self.session.rollback()
            message = str(error).lower()
            if self.session.get_bind().dialect.name == "sqlite" and ("locked" in message or "busy" in message):
                await _async_backoff()
                return None
            raise

    async def _touch_lease(self, job_id: str, worker_id: str, fence: int, now: datetime) -> bool:
        if not await self._lock_current_target(job_id):
            return False
        result = await self.session.execute(update(ToolJob).where(
            ToolJob.id == job_id, ToolJob.status == "running",
            ToolJob.lease_owner == worker_id, ToolJob.fence == fence,
            ToolJob.lease_until > now, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(updated_at=now).execution_options(synchronize_session=False))
        return result.rowcount == 1

    async def heartbeat(self, job_id: str, worker_id: str, fence: int, lease_seconds: int = 30) -> bool:
        now = datetime.now(UTC)
        result = await self.session.execute(update(ToolJob).where(
            ToolJob.id == job_id, ToolJob.status == "running",
            ToolJob.lease_owner == worker_id, ToolJob.fence == fence,
            ToolJob.lease_until > now, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(lease_until=now + timedelta(seconds=max(5, min(lease_seconds, 300))), updated_at=now)
         .execution_options(synchronize_session=False))
        await self.session.commit()
        return result.rowcount == 1

    async def start_attempt(self, lease: JobLease, step_key: str = "run", max_attempts: int = 3) -> bool:
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        step = await self.session.scalar(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.step_key == step_key,
        ))
        if step is None:
            if await self.session.scalar(select(func.count(ToolStep.id)).where(ToolStep.job_id == lease.job_id)) >= MAX_STEPS_PER_JOB:
                await self.session.rollback()
                raise JobCommandError("任务步骤数量超过限制")
            step = ToolStep(
                id=str(uuid4()), job_id=lease.job_id, step_key=step_key, status="queued",
                input_digest=lease.job_id, attempt_count=0, max_attempts=max_attempts,
                external_state="not_started", created_at=now, updated_at=now,
            )
            self.session.add(step)
            await self.session.flush()
        if step.status == "succeeded":
            await self.session.rollback()
            return False
        # A lease can expire after creating an attempt but before the durable
        # external-call marker. Keep that attempt for audit and sequencing,
        # without charging it against the provider-attempt budget.
        consumed_attempts = await self.session.scalar(select(func.count(ToolAttempt.id)).where(
            ToolAttempt.step_id == step.id,
            or_(ToolAttempt.outcome.is_(None), ToolAttempt.outcome != "interrupted",
                ToolAttempt.external_state != "not_started"),
        ))
        if int(consumed_attempts or 0) >= min(5, step.max_attempts):
            await self.session.rollback()
            raise JobCommandError("步骤尝试次数已达上限")
        step.attempt_count += 1
        step.status = "running"
        step.external_state = "not_started"
        step.error_code = None
        step.next_run_at = None
        step.updated_at = now
        step.completed_at = None
        self.session.add(ToolAttempt(
            id=str(uuid4()), job_id=lease.job_id, step_id=step.id,
            attempt_number=step.attempt_count, started_at=now,
            external_state="not_started",
        ))
        await self._event(lease.job_id, "step_started", "正在执行任务步骤", {"step_key": step_key})
        await self.session.commit()
        return True

    async def mark_external_call(self, lease: JobLease, step_key: str = "run") -> bool:
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        step = await self.session.scalar(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.step_key == step_key,
            ToolStep.status == "running",
        ))
        if step is None:
            await self.session.rollback()
            return False
        step.external_state = "may_have_run"
        attempt = await self.session.scalar(select(ToolAttempt).where(
            ToolAttempt.step_id == step.id, ToolAttempt.attempt_number == step.attempt_count,
        ))
        if attempt:
            attempt.external_state = "may_have_run"
        await self._event(lease.job_id, "external_call_started", "正在等待外部服务结果", {"step_key": step_key})
        await self.session.commit()
        return True

    async def complete_step(
        self, lease: JobLease, result_payload: dict[str, Any], step_key: str = "run",
    ) -> bool:
        if _size(result_payload) > MAX_STEP_RESULT_BYTES:
            raise JobCommandError("步骤结果超过 1 MiB 限制")
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        step = await self.session.scalar(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.step_key == step_key,
            ToolStep.status == "running",
        ))
        if step is None:
            await self.session.rollback()
            return False
        step.status = "succeeded"
        step.result_json = _json(result_payload)
        step.external_state = "confirmed_success"
        step.error_code = None
        step.completed_at = now
        step.updated_at = now
        attempt = await self.session.scalar(select(ToolAttempt).where(
            ToolAttempt.step_id == step.id, ToolAttempt.attempt_number == step.attempt_count,
        ))
        if attempt:
            attempt.finished_at = now
            attempt.external_state = step.external_state
            attempt.outcome = "succeeded"
        await self._event(lease.job_id, "step_succeeded", "任务步骤已完成", {"step_key": step_key})
        await self.session.commit()
        return True

    async def complete_job(self, lease: JobLease, result_payload: dict[str, Any]) -> bool:
        if _size(result_payload) > MAX_JOB_RESULT_BYTES:
            raise JobCommandError("任务结果超过 4 MiB 限制")
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        result = await self.session.execute(update(ToolJob).where(
            ToolJob.id == lease.job_id, ToolJob.status == "running",
            ToolJob.lease_owner == lease.worker_id, ToolJob.fence == lease.fence,
            ToolJob.lease_until > now, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(status="succeeded", result_json=_json(result_payload), reason=None,
                 lease_owner=None, lease_until=None, fence=ToolJob.fence + 1,
                 completed_at=now, updated_at=now).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            await self.session.rollback()
            return False
        await self._event(lease.job_id, "succeeded", "任务已完成，结果已保存")
        await self.session.commit()
        return True

    async def complete_execution(
        self, lease: JobLease, result_payload: dict[str, Any], step_key: str = "run",
    ) -> bool:
        """Commit the successful step result and job result behind the same live fence."""
        if _size(result_payload) > MAX_STEP_RESULT_BYTES or _size(result_payload) > MAX_JOB_RESULT_BYTES:
            raise JobCommandError("任务结果超过允许的大小限制")
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        step = await self.session.scalar(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.step_key == step_key,
            ToolStep.status == "running",
        ))
        if step is None:
            await self.session.rollback()
            return False
        job_result = await self.session.execute(update(ToolJob).where(
            ToolJob.id == lease.job_id, ToolJob.status == "running",
            ToolJob.lease_owner == lease.worker_id, ToolJob.fence == lease.fence,
            ToolJob.lease_until > now, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(status="succeeded", result_json=_json(result_payload), reason=None,
                 lease_owner=None, lease_until=None, fence=ToolJob.fence + 1,
                 completed_at=now, updated_at=now).execution_options(synchronize_session=False))
        if job_result.rowcount != 1:
            await self.session.rollback()
            return False
        step.status = "succeeded"
        step.result_json = _json(result_payload)
        step.external_state = "confirmed_success"
        step.error_code = None
        step.completed_at = now
        step.updated_at = now
        attempt = await self.session.scalar(select(ToolAttempt).where(
            ToolAttempt.step_id == step.id, ToolAttempt.attempt_number == step.attempt_count,
        ))
        if attempt:
            attempt.finished_at = now
            attempt.external_state = "confirmed_success"
            attempt.outcome = "succeeded"
        await self._event(lease.job_id, "step_succeeded", "任务步骤已完成", {"step_key": step_key})
        await self._event(lease.job_id, "succeeded", "任务已完成，结果已保存")
        await self.session.commit()
        return True

    async def fail_step(
        self,
        lease: JobLease,
        error_code: str,
        *,
        retryable: bool,
        external_outcome: str,
        step_key: str = "run",
    ) -> bool:
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        step = await self.session.scalar(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.step_key == step_key,
            ToolStep.status == "running",
        ))
        job = await self.session.get(ToolJob, lease.job_id)
        if step is None or job is None:
            await self.session.rollback()
            return False
        attempt = await self.session.scalar(select(ToolAttempt).where(
            ToolAttempt.step_id == step.id, ToolAttempt.attempt_number == step.attempt_count,
        ))
        if attempt:
            attempt.finished_at = now
            attempt.external_state = external_outcome
            attempt.outcome = "unknown" if external_outcome == "unknown" else "failed"
            attempt.error_code = error_code[:80]
        if external_outcome == "unknown":
            job.status = "waiting_user"
            job.reason = "external_outcome_unknown"
            job.lease_owner = None
            job.lease_until = None
            job.fence += 1
            step.status = "waiting_user"
            step.external_state = "unknown"
            step.error_code = "external_outcome_unknown"
            event_type = "waiting_user"
            summary = "外部调用结果不确定，需要确认后才能重试"
        elif retryable and external_outcome in ("not_started", "confirmed_failure") and step.attempt_count < step.max_attempts and job.deadline_at > now:
            delay_seconds = min(60, 2 ** max(0, step.attempt_count - 1) + random.randint(0, 2))
            job.status = "retry_wait"
            job.reason = error_code[:80]
            job.next_run_at = now + timedelta(seconds=delay_seconds)
            job.lease_owner = None
            job.lease_until = None
            job.fence += 1
            step.status = "retry_wait"
            step.error_code = error_code[:80]
            step.next_run_at = job.next_run_at
            event_type = "retry_scheduled"
            summary = "安全重试已排队"
        else:
            job.status = "failed"
            job.reason = error_code[:80]
            job.lease_owner = None
            job.lease_until = None
            job.fence += 1
            job.completed_at = now
            step.status = "failed"
            step.error_code = error_code[:80]
            step.completed_at = now
            event_type = "failed"
            summary = "任务执行失败"
        job.updated_at = now
        step.updated_at = now
        await self._event(lease.job_id, event_type, summary, {"step_key": step_key, "error_code": step.error_code})
        await self.session.commit()
        return True

    async def fail_claimed_job(self, lease: JobLease, reason: str, summary: str) -> bool:
        now = datetime.now(UTC)
        if not await self._touch_lease(lease.job_id, lease.worker_id, lease.fence, now):
            await self.session.rollback()
            return False
        result = await self.session.execute(update(ToolJob).where(
            ToolJob.id == lease.job_id, ToolJob.status == "running",
            ToolJob.lease_owner == lease.worker_id, ToolJob.fence == lease.fence,
            ToolJob.lease_until > now, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(status="failed", reason=reason[:80], lease_owner=None, lease_until=None,
                 fence=ToolJob.fence + 1, completed_at=now, updated_at=now)
         .execution_options(synchronize_session=False))
        if result.rowcount != 1:
            await self.session.rollback()
            return False
        steps = (await self.session.scalars(select(ToolStep).where(
            ToolStep.job_id == lease.job_id, ToolStep.status.in_(("queued", "retry_wait", "running")),
        ))).all()
        for step in steps:
            step.status = "failed"
            step.error_code = reason[:80]
            step.completed_at = now
            step.updated_at = now
            if step.attempt_count:
                attempt = await self.session.scalar(select(ToolAttempt).where(
                    ToolAttempt.step_id == step.id,
                    ToolAttempt.attempt_number == step.attempt_count,
                ))
                if attempt and attempt.finished_at is None:
                    attempt.finished_at = now
                    attempt.outcome = "failed"
                    attempt.error_code = reason[:80]
        await self._event(lease.job_id, "failed", summary, {"reason": reason[:80]})
        await self.session.commit()
        return True

    async def _owned_job(
        self, principal_type: str, principal_id: str, site_id: str, target_id: str, job_id: str,
    ) -> ToolJob | None:
        return await self.session.scalar(select(ToolJob).where(
            ToolJob.id == job_id, ToolJob.principal_type == principal_type,
            ToolJob.principal_id == principal_id, ToolJob.site_id == site_id,
            ToolJob.target_type == "tour_session", ToolJob.target_id == target_id,
        ))

    async def get_job(
        self, principal_type: str, principal_id: str, site_id: str, target_id: str, job_id: str,
    ) -> dict[str, Any] | None:
        job = await self._owned_job(principal_type, principal_id, site_id, target_id, job_id)
        return await self._view(job) if job else None

    async def list_jobs(
        self, principal_type: str, principal_id: str, site_id: str, target_id: str, limit: int = 50,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.principal_type == principal_type, ToolJob.principal_id == principal_id,
            ToolJob.site_id == site_id, ToolJob.target_type == "tour_session",
            ToolJob.target_id == target_id,
        ).order_by(ToolJob.created_at.desc()).limit(limit))).all()
        return [await self._view(job, include_steps=False) for job in jobs]

    async def list_events(
        self, principal_type: str, principal_id: str, site_id: str,
        target_id: str, job_id: str, after_seq: int = 0, limit: int = 100,
    ) -> dict[str, Any] | None:
        job = await self._owned_job(principal_type, principal_id, site_id, target_id, job_id)
        if job is None:
            return None
        limit = max(1, min(limit, MAX_EVENT_PAGE))
        after_seq = max(0, after_seq)
        minimum = int(await self.session.scalar(select(func.coalesce(func.min(ToolEvent.seq), 0)).where(
            ToolEvent.job_id == job_id,
        )) or 0)
        latest = int(await self.session.scalar(select(func.coalesce(func.max(ToolEvent.seq), 0)).where(
            ToolEvent.job_id == job_id,
        )) or 0)
        snapshot_required = bool(minimum and after_seq < minimum - 1)
        rows = (await self.session.scalars(select(ToolEvent).where(
            ToolEvent.job_id == job_id, ToolEvent.seq > after_seq,
        ).order_by(ToolEvent.seq).limit(limit))).all()
        return {
            "items": [{"seq": row.seq, "type": row.event_type, "summary": row.summary,
                       "payload": _decode(row.payload_json),
                       "created_at": row.created_at.isoformat() if row.created_at else None}
                      for row in rows],
            "next_seq": rows[-1].seq if rows else after_seq,
            "snapshot_required": snapshot_required,
            "latest_seq": latest,
        }

    async def _record_command_receipt(
        self, job: ToolJob, command: str, key: str, digest: str, now: datetime,
    ) -> None:
        self.session.add(ToolCommandReceipt(
            id=str(uuid4()), principal_type=job.principal_type, principal_id=job.principal_id,
            command=command, key=key, payload_digest=digest, job_id=job.id,
            response_json=_json({"job_id": job.id}), expires_at=now + RECEIPT_TTL, created_at=now,
        ))

    async def request_cancel(
        self, principal_type: str, principal_id: str, site_id: str, target_id: str,
        job_id: str, idempotency_key: str,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        digest = _digest({"job_id": job_id, "command": "cancel"})
        receipt = await self._receipt(principal_type, principal_id, "cancel", idempotency_key, digest)
        if receipt:
            return await self._replay_view(receipt)
        job = await self._owned_job(principal_type, principal_id, site_id, target_id, job_id)
        if job is None:
            await self.session.rollback()
            return None
        if self.session.get_bind().dialect.name == "postgresql":
            # Serialize with mark_external_call, which locks this job before changing the step.
            job = await self.session.scalar(select(ToolJob).where(
                ToolJob.id == job.id,
            ).with_for_update().execution_options(populate_existing=True))
        if job.status in ACTIVE_STATES:
            prior_unknown = job.reason == "external_outcome_unknown"
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status.in_(ACTIVE_STATES), ToolJob.fence == job.fence,
            ).values(status="cancelled", reason="cancelled_by_user",
                     lease_owner=None, lease_until=None, fence=ToolJob.fence + 1,
                     completed_at=now, updated_at=now).execution_options(synchronize_session=False))
            if result.rowcount == 1:
                self.session.expire_all()
                job = await self.session.get(ToolJob, job_id)
                uncertain = prior_unknown
                uncertain = await self._close_steps(job.id, "cancelled", "cancelled", now) or uncertain
                job.reason = "cancelled_external_outcome_unknown" if uncertain else "cancelled_by_user"
                await self._event(job.id, "cancelled", "任务已取消", {
                    "external_outcome_unknown": uncertain,
                })
                job.status = "cancelled"
                job.reason = "cancelled_external_outcome_unknown" if uncertain else "cancelled_by_user"
                job.lease_owner = None
                job.lease_until = None
                job.completed_at = now
            else:
                await self.session.rollback()
                receipt = await self._receipt(principal_type, principal_id, "cancel", idempotency_key, digest)
                replay = await self._replay_view(receipt)
                if replay is not None:
                    return replay
                await self.session.rollback()
                raise IdempotencyConflict("任务状态已变化，请使用相同幂等键重试取消")
        await self._record_command_receipt(job, "cancel", idempotency_key, digest, now)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            receipt = await self._receipt(principal_type, principal_id, "cancel", idempotency_key, digest)
            return await self._replay_view(receipt)
        return await self.get_job(principal_type, principal_id, site_id, target_id, job_id)

    async def manual_retry(
        self, principal_type: str, principal_id: str, site_id: str, target_id: str,
        job_id: str, idempotency_key: str, confirm_duplicate_risk: bool = False,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        digest = _digest({"job_id": job_id, "command": "retry", "confirm_duplicate_risk": confirm_duplicate_risk})
        receipt = await self._receipt(principal_type, principal_id, "retry", idempotency_key, digest)
        if receipt:
            return await self._replay_view(receipt)
        job = await self._owned_job(principal_type, principal_id, site_id, target_id, job_id)
        if job is None:
            await self.session.rollback()
            return None
        if job.status not in ("failed", "waiting_user"):
            raise JobCommandError("只有失败或待确认任务可以重试")
        if job.recovery_mode == "query_only":
            raise JobCommandError("该任务只支持查询，不允许重新执行")
        if job.reason == "external_outcome_unknown" and not confirm_duplicate_risk:
            raise JobCommandError("该任务可能已产生外部结果；确认重复执行风险后才能重试")
        if not job.retry_safe and not confirm_duplicate_risk:
            raise JobCommandError("该工具未声明可安全重试；确认重复执行风险后才能重试")
        if job.reason not in (
            "external_outcome_unknown", "handler_error", "handler_timeout",
            "job_timeout", "provider_unavailable",
        ):
            raise JobCommandError("该失败原因不允许人工重试")
        if job.manual_retry_count >= 2:
            raise JobCommandError("任务已达到人工重试上限")
        if _aware(job.deadline_at) <= now:
            raise JobCommandError("任务已超过截止时间，不能重试")
        if await self.session.scalar(select(TourSession.id).where(
            TourSession.id == target_id, TourSession.owner_id == principal_id,
            TourSession.site_id == site_id, TourSession.version == job.base_revision,
            TourSession.deleted_at.is_(None),
        )) is None:
            raise JobCommandError("游览内容已更新，任务不能重试")
        steps = (await self.session.scalars(select(ToolStep).where(ToolStep.job_id == job.id))).all()
        retry_steps = [step for step in steps if step.status != "succeeded"]
        if not retry_steps:
            raise JobCommandError("任务已完成的全部步骤不能重复执行")
        if any(step.attempt_count >= 5 for step in retry_steps):
            raise JobCommandError("步骤已达到总尝试上限")
        old_status, old_fence = job.status, job.fence
        changed = await self.session.execute(update(ToolJob).where(
            ToolJob.id == job.id, ToolJob.status == old_status, ToolJob.fence == old_fence,
            ToolJob.manual_retry_count < 2, ToolJob.deadline_at > now,
            self._target_current_clause(),
        ).values(status="queued", reason=None, next_run_at=now,
                 manual_retry_count=ToolJob.manual_retry_count + 1,
                 lease_owner=None, lease_until=None, fence=ToolJob.fence + 1,
                 completed_at=None, updated_at=now).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            await self.session.rollback()
            receipt = await self._receipt(principal_type, principal_id, "retry", idempotency_key, digest)
            replay = await self._replay_view(receipt)
            if replay:
                return replay
            raise JobCommandError("任务状态已变化，请刷新后重试")
        job.status = "queued"
        job.reason = None
        job.next_run_at = now
        job.manual_retry_count += 1
        job.lease_owner = None
        job.lease_until = None
        job.fence += 1
        job.completed_at = None
        job.updated_at = now
        for step in retry_steps:
            step.status = "queued"
            step.max_attempts = 5 if job.retry_safe else step.attempt_count + 1
            step.error_code = None
            step.external_state = "not_started"
            step.next_run_at = None
            step.completed_at = None
            step.updated_at = now
        self.session.add(ToolCommandReceipt(
            id=str(uuid4()), principal_type=principal_type, principal_id=principal_id,
            command="retry", key=idempotency_key, payload_digest=digest,
            job_id=job.id, response_json=_json({"job_id": job.id}),
            expires_at=now + RECEIPT_TTL, created_at=now,
        ))
        await self._event(job.id, "retry_requested", "已按用户确认重新排队", {
            "manual_retry_count": job.manual_retry_count,
            "duplicate_risk_confirmed": confirm_duplicate_risk,
        })
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            receipt = await self._receipt(principal_type, principal_id, "retry", idempotency_key, digest)
            return await self._replay_view(receipt)
        return await self.get_job(principal_type, principal_id, site_id, target_id, job_id)

    async def mark_target_revision_changed(self, session_id: str, current_version: int, deleted: bool = False) -> int:
        now = datetime.now(UTC)
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.target_type == "tour_session", ToolJob.target_id == session_id,
            ToolJob.base_revision != current_version, ToolJob.status.in_(ACTIVE_STATES),
        ))).all()
        changed = 0
        for job in jobs:
            status = "cancelled" if deleted else "stale"
            reason = "tour_deleted" if deleted else "target_revision_changed"
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status.in_(ACTIVE_STATES), ToolJob.fence == job.fence,
            ).values(status=status, reason=reason, lease_owner=None, lease_until=None,
                     fence=ToolJob.fence + 1, completed_at=now, updated_at=now)
             .execution_options(synchronize_session=False))
            if result.rowcount == 1:
                uncertain = await self._close_steps(job.id, status, reason, now)
                await self._event(
                    job.id, status,
                    "任务目标已删除" if deleted else "游览内容已更新，任务已标记为过期",
                    {"external_outcome_unknown": uncertain},
                )
                changed += 1
        return changed

    async def mark_target_progress_changed(self, session_id: str, current_progress_version: int) -> int:
        now = datetime.now(UTC)
        jobs = (await self.session.scalars(select(ToolJob).where(
            ToolJob.target_type == "tour_session", ToolJob.target_id == session_id,
            ToolJob.progress_version.is_not(None),
            ToolJob.progress_version != current_progress_version,
            ToolJob.status.in_(ACTIVE_STATES),
        ))).all()
        changed = 0
        for job in jobs:
            result = await self.session.execute(update(ToolJob).where(
                ToolJob.id == job.id, ToolJob.status.in_(ACTIVE_STATES), ToolJob.fence == job.fence,
            ).values(status="stale", reason="target_progress_changed", lease_owner=None,
                     lease_until=None, fence=ToolJob.fence + 1, completed_at=now, updated_at=now)
             .execution_options(synchronize_session=False))
            if result.rowcount == 1:
                uncertain = await self._close_steps(job.id, "stale", "target_progress_changed", now)
                await self._event(job.id, "stale", "游览进度已更新，任务结果需要重新确认", {
                    "external_outcome_unknown": uncertain,
                })
                changed += 1
        return changed

    async def purge_session(self, session_id: str) -> None:
        job_ids = select(ToolJob.id).where(ToolJob.target_id == session_id)
        await self.session.execute(delete(ToolCommandReceipt).where(ToolCommandReceipt.job_id.in_(job_ids)))
        await self.session.execute(delete(ToolAttempt).where(ToolAttempt.job_id.in_(job_ids)))
        await self.session.execute(delete(ToolEvent).where(ToolEvent.job_id.in_(job_ids)))
        await self.session.execute(delete(ToolStep).where(ToolStep.job_id.in_(job_ids)))
        await self.session.execute(delete(ToolJob).where(ToolJob.target_id == session_id))

    async def cleanup_receipts(self, now: datetime | None = None) -> int:
        result = await self.session.execute(delete(ToolCommandReceipt).where(
            ToolCommandReceipt.expires_at <= (now or datetime.now(UTC)),
        ))
        await self.session.commit()
        return int(result.rowcount or 0)


async def _async_backoff() -> None:
    import asyncio

    await asyncio.sleep(random.uniform(0.01, 0.05))
