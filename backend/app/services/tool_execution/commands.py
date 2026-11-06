from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tool_execution import JobCommandError, ToolExecutionRepository
from app.schemas.tool_execution import ToolPrincipal, ToolTarget
from app.services.tool_execution.registry import ToolRegistry


async def enqueue_registered_tool(
    session: AsyncSession,
    registry: ToolRegistry,
    *,
    principal: ToolPrincipal,
    site_id: str,
    target: ToolTarget,
    tool_name: str,
    tool_version: str,
    workflow_schema_version: str,
    payload: dict[str, Any] | BaseModel,
    idempotency_key: str,
    deadline_seconds: int = 3600,
    commit: bool = True,
) -> dict[str, Any]:
    handler = registry.get(tool_name, tool_version, workflow_schema_version)
    if handler is None:
        raise JobCommandError("该工具版本当前未注册")
    if isinstance(payload, BaseModel):
        payload_value = payload.model_dump(mode="json")
    else:
        payload_value = payload
    validated = handler.input_model.model_validate(payload_value)
    normalized_payload = validated.model_dump(mode="json")
    return await ToolExecutionRepository(session).create_job(
        principal_type=principal.type,
        principal_id=principal.id,
        site_id=site_id,
        tool_name=handler.name,
        tool_version=handler.version,
        workflow_schema_version=handler.workflow_schema_version,
        recovery_mode=handler.recovery_mode,
        retry_safe=handler.retry_safe,
        target=target.model_dump(mode="json"),
        payload=normalized_payload,
        idempotency_key=idempotency_key,
        deadline_seconds=deadline_seconds,
        max_attempts=handler.max_attempts if handler.retry_safe else 1,
        commit=commit,
    )
