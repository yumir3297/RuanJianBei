from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, Callable
from time import monotonic


class AudioTaskGroup:
    """Schedule bounded audio work and cancel/join it as one request scope."""

    def __init__(self, worker: Callable[..., object], concurrency: int = 3) -> None:
        self._worker = worker
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: list[asyncio.Task[None]] = []

    @property
    def tasks(self) -> tuple[asyncio.Task[None], ...]:
        return tuple(self._tasks)

    @property
    def pending(self) -> tuple[asyncio.Task[None], ...]:
        return tuple(task for task in self._tasks if not task.done())

    def schedule(self, sentence: str, *, notify=None) -> asyncio.Task[None]:
        previous = self._tasks[-1] if self._tasks else None
        task = asyncio.create_task(
            self._worker(sentence, previous=previous, semaphore=self._semaphore, notify=notify)
        )
        self._tasks.append(task)
        return task

    async def cancel(self) -> None:
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


async def cancel_and_join(*tasks: asyncio.Task[object] | None) -> None:
    """Cancel unfinished stream workers and wait until every worker has exited."""
    active = [task for task in tasks if task is not None]
    for task in active:
        if not task.done():
            task.cancel()
    if active:
        await asyncio.gather(*active, return_exceptions=True)


async def forward_events(
    queue: asyncio.Queue[tuple[str, object | None]],
    source: AsyncIterable[object],
    event_kind: str,
    error_kind: str,
    done_kind: str,
) -> None:
    """Forward a producer stream through the pipeline mux with terminal signals."""
    try:
        async for item in source:
            await queue.put((event_kind, item))
    except Exception as exc:
        await queue.put((error_kind, exc))
    finally:
        await queue.put((done_kind, None))


async def forward_tts_events(
    session,
    queue: asyncio.Queue[tuple[str, object | None]],
    finish_requested: asyncio.Event,
    completion_timeout: float = 12.0,
) -> None:
    """Connect a streaming TTS session and forward events to the pipeline mux."""
    try:
        await session.connect()
        await queue.put(("tts_connected", None))
        finish_wait_started: float | None = None
        while True:
            event = await session.receive(timeout=1.0)
            if event is None:
                if finish_requested.is_set():
                    finish_wait_started = finish_wait_started or monotonic()
                    if monotonic() - finish_wait_started >= completion_timeout:
                        raise TimeoutError("流式 TTS 完成事件等待超时")
                continue
            await queue.put(("tts", event))
            if event.type in {"done", "error"}:
                break
    except Exception as exc:
        await queue.put(("tts_connect_error", exc))
