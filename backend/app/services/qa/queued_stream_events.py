from __future__ import annotations

import asyncio
from collections.abc import Iterable

from app.services.qa.stream_events import StreamEvent


class QueuedStreamEvents:
    """FIFO buffer for response events produced by background audio tasks."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue()

    async def publish(self, events: Iterable[StreamEvent], *, notify=None) -> None:
        for event in events:
            await self._queue.put(event)
        if notify is not None:
            await notify()

    def drain(self) -> tuple[StreamEvent, ...]:
        drained: list[StreamEvent] = []
        while True:
            try:
                drained.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                return tuple(drained)
