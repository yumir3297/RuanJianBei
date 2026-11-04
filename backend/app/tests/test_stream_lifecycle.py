import asyncio

import pytest

from app.services.qa.stream_lifecycle import cancel_and_join


@pytest.mark.asyncio
async def test_cancel_and_join_waits_for_cancelled_stream_tasks():
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def worker():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    task = asyncio.create_task(worker())
    await started.wait()

    await cancel_and_join(task)

    assert task.cancelled()
    assert cleaned.is_set()
