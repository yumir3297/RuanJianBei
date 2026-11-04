from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
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
