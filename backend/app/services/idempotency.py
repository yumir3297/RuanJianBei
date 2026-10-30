from __future__ import annotations

import asyncio
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


class IdempotencyConflict(Exception):
    """A key was reused for a different request fingerprint."""


class IdempotencyCapacityExceeded(Exception):
    """The coordinator is at its in-flight operation limit."""


@dataclass
class _Entry:
    fingerprint: str
    task: asyncio.Task[Any]
    expires_at: float | None = None
    result: Any = None
    size: int = 0


class IdempotencyCoordinator:
    """Bounded process-local single-flight and short response cache."""

    def __init__(self, ttl_seconds: float = 300, max_entries: int = 128, max_bytes: int = 1024 * 1024):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: OrderedDict[tuple[str, str], _Entry] = OrderedDict()
        self._bytes = 0
        self._lock = asyncio.Lock()

    async def run(self, scope: str, key: str, fingerprint: str, operation: Callable[[], Awaitable[Any]], on_reuse: Callable[[], Awaitable[Any]] | None = None) -> Any:
        cache_key = (scope, key)
        async with self._lock:
            self._prune()
            entry = self._entries.get(cache_key)
            if entry is not None:
                if entry.fingerprint != fingerprint:
                    raise IdempotencyConflict
                self._entries.move_to_end(cache_key)
                task = entry.task
            else:
                while len(self._entries) >= self.max_entries:
                    removable = next((candidate for candidate, item in self._entries.items() if item.expires_at is not None or item.task.done()), None)
                    if removable is None:
                        raise IdempotencyCapacityExceeded
                    removed = self._entries.pop(removable)
                    self._bytes -= removed.size
                task = asyncio.create_task(self._compute(cache_key, fingerprint, operation))
                self._entries[cache_key] = _Entry(fingerprint=fingerprint, task=task)
                self._trim()
        if entry is not None and on_reuse is not None:
            await on_reuse()
        return await asyncio.shield(task)

    async def _compute(self, cache_key: tuple[str, str], fingerprint: str, operation: Callable[[], Awaitable[Any]]) -> Any:
        try:
            result = await operation()
            encoded_size = len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            async with self._lock:
                entry = self._entries.get(cache_key)
                if entry is not None and entry.fingerprint == fingerprint and entry.task is asyncio.current_task():
                    if encoded_size <= self.max_bytes:
                        entry.result = result
                        entry.size = encoded_size
                        entry.expires_at = time.monotonic() + self.ttl_seconds
                        self._bytes += encoded_size
                        self._trim()
                    else:
                        self._entries.pop(cache_key, None)
            return result
        except BaseException:
            async with self._lock:
                entry = self._entries.get(cache_key)
                if entry is not None and entry.task is asyncio.current_task():
                    self._entries.pop(cache_key, None)
            raise

    def _prune(self) -> None:
        now = time.monotonic()
        for cache_key, entry in list(self._entries.items()):
            if entry.expires_at is not None and entry.expires_at <= now:
                self._entries.pop(cache_key, None)
                self._bytes -= entry.size

    def _trim(self) -> None:
        while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
            cache_key, entry = next(iter(self._entries.items()))
            # Never evict an operation while it is running; completed cache
            # records are identifiable before their wrapping task returns.
            if entry.expires_at is None and not entry.task.done():
                self._entries.move_to_end(cache_key)
                if all(not candidate.task.done() for candidate in self._entries.values()):
                    break
                continue
            self._entries.pop(cache_key, None)
            self._bytes -= entry.size


idempotency_coordinator = IdempotencyCoordinator()
