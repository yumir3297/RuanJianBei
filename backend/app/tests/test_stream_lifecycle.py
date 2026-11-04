import asyncio

import pytest

from app.services.qa.stream_lifecycle import cancel_and_join, forward_events


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


@pytest.mark.asyncio
async def test_forward_events_always_sends_done_after_source_failure():
    queue = asyncio.Queue()

    async def source():
        yield "partial"
        raise RuntimeError("provider disconnected")

    await forward_events(queue, source(), "llm", "llm_error", "llm_done")

    assert await queue.get() == ("llm", "partial")
    kind, error = await queue.get()
    assert kind == "llm_error"
    assert isinstance(error, RuntimeError)
    assert str(error) == "provider disconnected"
    assert await queue.get() == ("llm_done", None)
