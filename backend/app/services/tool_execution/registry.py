from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Awaitable, Callable, Literal, Type

from pydantic import BaseModel, ConfigDict


ToolCallable = Callable[[BaseModel, "ToolContext"], Awaitable[BaseModel | dict[str, Any]]]
ToolResultPersister = Callable[[Any, Any, BaseModel], Awaitable[None]]


class ToolStepError(Exception):
    """A handler error with an explicit retry and external-outcome classification."""

    def __init__(
        self,
        code: str,
        *,
        retryable: bool = False,
        external_outcome: Literal["not_started", "confirmed_failure", "unknown"] = "not_started",
    ) -> None:
        self.code = code[:80] if re.fullmatch(r"[a-zA-Z0-9_.-]{1,80}", code) else "handler_error"
        self.retryable = retryable
        self.external_outcome = external_outcome
        super().__init__(self.code)


@dataclass(frozen=True)
class ToolHandler:
    name: str
    version: str
    workflow_schema_version: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    execute: ToolCallable
    retry_safe: bool = False
    max_attempts: int = 3
    timeout_seconds: int = 120
    recovery_mode: Literal["query_only", "manual_retry", "durable_resume"] = "durable_resume"
    persist_result: ToolResultPersister | None = None

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 100:
            raise ValueError("tool name must be 1-100 characters")
        if not self.version or len(self.version) > 40:
            raise ValueError("tool version must be 1-40 characters")
        if not self.workflow_schema_version or len(self.workflow_schema_version) > 40:
            raise ValueError("workflow schema version must be 1-40 characters")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if not isinstance(self.retry_safe, bool):
            raise ValueError("retry_safe must be an explicit boolean")
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        for model_type in (self.input_model, self.output_model):
            if not issubclass(model_type, BaseModel):
                raise TypeError("tool schemas must be Pydantic models")
            if model_type.model_config.get("extra") != "forbid":
                raise ValueError("tool schemas must reject unknown fields")


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], ToolHandler] = {}

    def register(self, handler: ToolHandler) -> None:
        key = (handler.name, handler.version)
        if key in self._handlers:
            raise ValueError(f"duplicate tool registration: {key}")
        self._handlers[key] = handler

    def get(self, name: str, version: str, workflow_schema_version: str) -> ToolHandler | None:
        handler = self._handlers.get((name, version))
        if handler is None or handler.workflow_schema_version != workflow_schema_version:
            return None
        return handler

    def __len__(self) -> int:
        return len(self._handlers)

    def names(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(sorted((name, version, handler.workflow_schema_version)
                            for (name, version), handler in self._handlers.items()))


class ToolContext:
    def __init__(self, session_factory: Any, lease: Any, step_key: str = "run") -> None:
        self._session_factory = session_factory
        self._lease = lease
        self._step_key = step_key
        self.external_call_started = False

    @property
    def lease(self) -> Any:
        return self._lease

    async def mark_external_call(self) -> None:
        from app.repositories.tool_execution import ToolExecutionRepository

        async with self._session_factory() as session:
            updated = await ToolExecutionRepository(session).mark_external_call(self._lease, self._step_key)
        if not updated:
            raise ToolStepError("lease_lost", external_outcome="unknown")
        self.external_call_started = True
