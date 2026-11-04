import asyncio

import pytest

from app.services.qa.stream_lifecycle import AudioTaskGroup, cancel_and_join, forward_events, forward_tts_events


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


@pytest.mark.asyncio
async def test_forward_tts_events_marks_connection_and_forwards_terminal_event():
    queue = asyncio.Queue()

    class Session:
        def __init__(self):
            self.events = iter([SimpleEvent("audio_chunk"), SimpleEvent("done")])

        async def connect(self):
            return None

        async def receive(self, timeout=None):
            del timeout
            return next(self.events)

    await forward_tts_events(Session(), queue, asyncio.Event())

    assert await queue.get() == ("tts_connected", None)
    kind, event = await queue.get()
    assert kind == "tts"
    assert event.type == "audio_chunk"
    kind, event = await queue.get()
    assert kind == "tts"
    assert event.type == "done"


class SimpleEvent:
    def __init__(self, event_type):
        self.type = event_type


@pytest.mark.asyncio
async def test_audio_task_group_cancels_and_joins_scheduled_audio():
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def worker(sentence, *, previous, semaphore, notify):
        del sentence, previous, semaphore, notify
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    tasks = AudioTaskGroup(worker)
    tasks.schedule("一句话")
    await started.wait()

    await tasks.cancel()

    assert cleaned.is_set()
    assert tasks.pending == ()
