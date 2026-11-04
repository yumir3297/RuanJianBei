import asyncio

import pytest

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_completion import AudioTaskDrainer
from app.services.qa.stream_events import StreamEvent


@pytest.mark.asyncio
async def test_audio_task_drainer_waits_for_tasks_then_emits_events_in_fifo_order():
    completed = []

    async def task(name):
        await asyncio.sleep(0)
        completed.append(name)

    queue = QueuedStreamEvents()
    await queue.publish([
        StreamEvent(type="audio", data={"index": 1}),
        StreamEvent(type="avatar", data={"index": 2}),
    ])

    async def epoch_is_current():
        return True

    async def cancel_audio():
        pytest.fail("audio should not be cancelled")

    drainer = AudioTaskDrainer(
        tasks=[asyncio.create_task(task("first")), asyncio.create_task(task("second"))],
        audio_events=queue,
        epoch_is_current=epoch_is_current,
        cancel_audio=cancel_audio,
    )

    emitted = [event async for event in drainer.events()]

    assert completed == ["first", "second"]
    assert [event.data for event in emitted] == [{"index": 1}, {"index": 2}]
    assert not drainer.visibility_changed


@pytest.mark.asyncio
async def test_audio_task_drainer_cancels_and_withholds_events_after_epoch_change():
    queue = QueuedStreamEvents()
    pending = asyncio.create_task(asyncio.sleep(60))
    await queue.publish([StreamEvent(type="audio", data={"stale": True})])
    cancelled = False

    async def epoch_is_current():
        return False

    async def cancel_audio():
        nonlocal cancelled
        cancelled = True
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)

    drainer = AudioTaskDrainer(
        tasks=[asyncio.create_task(asyncio.sleep(0)), pending],
        audio_events=queue,
        epoch_is_current=epoch_is_current,
        cancel_audio=cancel_audio,
    )

    emitted = [event async for event in drainer.events()]

    assert emitted == []
    assert cancelled
    assert pending.cancelled()
    assert drainer.visibility_changed
    assert [event.data for event in queue.drain()] == [{"stale": True}]
