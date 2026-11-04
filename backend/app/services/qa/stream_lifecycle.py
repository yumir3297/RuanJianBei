from __future__ import annotations

import asyncio
async def cancel_and_join(*tasks: asyncio.Task[object] | None) -> None:
    """Cancel unfinished stream workers and wait until every worker has exited."""
    active = [task for task in tasks if task is not None]
    for task in active:
        if not task.done():
            task.cancel()
    if active:
        await asyncio.gather(*active, return_exceptions=True)
