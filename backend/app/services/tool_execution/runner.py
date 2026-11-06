from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from app.repositories.tool_execution import (
    JobCommandError,
    JobLease,
    LeaseLost,
    MAX_STEP_RESULT_BYTES,
    ToolExecutionRepository,
)
from app.services.tool_execution.registry import ToolContext, ToolHandler, ToolRegistry, ToolStepError

_ORPHANED_TASKS: set[asyncio.Task[Any]] = set()


class ToolRunner:
    def __init__(
        self,
        session_factory: Any,
        registry: ToolRegistry,
        *,
        lease_seconds: int = 30,
        heartbeat_seconds: int = 10,
    ) -> None:
        self.session_factory = session_factory
        self.registry = registry
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds

    async def run_one(self, worker_id: str) -> bool:
        async with self.session_factory() as session:
            repository = ToolExecutionRepository(session)
            lease = await repository.claim_next(worker_id, self.lease_seconds)
        if lease is None:
            return False
        handler = self.registry.get(
            lease.tool_name, lease.tool_version, lease.workflow_schema_version,
        )
        if handler is None:
            async with self.session_factory() as session:
                await ToolExecutionRepository(session).fail_claimed_job(
                    lease, "handler_version_unsupported", "没有与任务版本兼容的执行器",
                )
            return True
        try:
            parsed_input = handler.input_model.model_validate(lease.input_payload)
        except ValidationError:
            async with self.session_factory() as session:
                await ToolExecutionRepository(session).fail_claimed_job(
                    lease, "invalid_persisted_input", "任务输入不符合固定版本的工具结构",
                )
            return True

        async with self.session_factory() as session:
            repository = ToolExecutionRepository(session)
            try:
                started = await repository.start_attempt(lease, max_attempts=handler.max_attempts)
            except JobCommandError:
                await repository.fail_claimed_job(
                    lease, "attempt_limit", "任务达到执行尝试上限",
                )
                return True
            if not started:
                return True
            context = ToolContext(self.session_factory, lease)
            try:
                raw_output = await self._execute_with_heartbeat(handler, parsed_input, context, lease)
                parsed_output = handler.output_model.model_validate(raw_output)
                output = parsed_output.model_dump(mode="json")
                if len(json.dumps(output, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_STEP_RESULT_BYTES:
                    raise ToolStepError(
                        "result_too_large",
                        external_outcome="unknown" if context.external_call_started else "confirmed_failure",
                    )
            except LeaseLost:
                await session.rollback()
            except ToolStepError as error:
                external_outcome = error.external_outcome
                if context.external_call_started and external_outcome == "not_started":
                    external_outcome = "unknown"
                await repository.fail_step(
                    lease, error.code, retryable=error.retryable,
                    external_outcome=external_outcome,
                )
            except asyncio.TimeoutError:
                await repository.fail_step(
                    lease, "handler_timeout", retryable=handler.retry_safe and not context.external_call_started,
                    external_outcome="unknown" if context.external_call_started else "not_started",
                )
            except ValidationError:
                await repository.fail_step(
                    lease, "invalid_handler_output", retryable=False,
                    external_outcome="unknown" if context.external_call_started else "not_started",
                )
            except asyncio.CancelledError:
                await session.rollback()
                raise
            except Exception:
                await repository.fail_step(
                    lease, "handler_error", retryable=False,
                    external_outcome="unknown" if context.external_call_started else "not_started",
                )
            else:
                # Keep persistence failures out of handler-error classification; lease expiry will recover them.
                await repository.complete_execution(lease, output)
        return True

    async def _execute_with_heartbeat(
        self,
        handler: ToolHandler,
        payload: Any,
        context: ToolContext,
        lease: JobLease,
    ) -> Any:
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(self._heartbeat(lease, stop_heartbeat))
        timeout_seconds = min(
            handler.timeout_seconds,
            max(1, int((_aware(lease.deadline_at) - datetime.now(UTC)).total_seconds())),
        )
        execution_task = asyncio.create_task(handler.execute(payload, context))
        timeout_task = asyncio.create_task(asyncio.sleep(timeout_seconds))
        try:
            done, _ = await asyncio.wait(
                (execution_task, heartbeat_task, timeout_task), return_when=asyncio.FIRST_COMPLETED,
            )
            if heartbeat_task in done:
                try:
                    lease_alive = heartbeat_task.result()
                except Exception as error:
                    _cancel_detach(execution_task)
                    raise LeaseLost("lease heartbeat failed") from error
                if not lease_alive:
                    _cancel_detach(execution_task)
                    raise LeaseLost("lease was lost")
            if timeout_task in done and execution_task not in done:
                _cancel_detach(execution_task)
                raise asyncio.TimeoutError
            return await execution_task
        finally:
            stop_heartbeat.set()
            if not heartbeat_task.done():
                heartbeat_task.cancel()
            if not timeout_task.done():
                timeout_task.cancel()
            await _settle(heartbeat_task)
            await _settle(timeout_task)

    async def _heartbeat(self, lease: JobLease, stop: asyncio.Event) -> bool:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.heartbeat_seconds)
                return True
            except asyncio.TimeoutError:
                pass
            async with self.session_factory() as session:
                alive = await ToolExecutionRepository(session).heartbeat(
                    lease.job_id, lease.worker_id, lease.fence, self.lease_seconds,
                )
            if not alive:
                return False
        return True


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def _settle(task: asyncio.Task[Any]) -> None:
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


def _cancel_detach(task: asyncio.Task[Any]) -> None:
    task.cancel()
    _ORPHANED_TASKS.add(task)

    def discard(completed: asyncio.Task[Any]) -> None:
        _ORPHANED_TASKS.discard(completed)
        try:
            completed.exception()
        except (asyncio.CancelledError, Exception):
            pass

    task.add_done_callback(discard)
