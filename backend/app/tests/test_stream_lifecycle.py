import asyncio

import pytest

from app.services.qa.stream_lifecycle import (
    AudioTaskGroup,
    StreamProducerGroup,
    cancel_and_join,
    forward_events,
    forward_tts_events,
    stream_response_scope,
)


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
async def test_response_scope_closes_producers_on_normal_completion_without_cancelling_audio():
    state = {"closed": False, "audio_cancelled": False}

    class Producers:
        async def close(self):
            state["closed"] = True

    async def cancel_audio():
        state["audio_cancelled"] = True

    async with stream_response_scope(Producers(), cancel_audio):
        pass

    assert state == {"closed": True, "audio_cancelled": False}


@pytest.mark.asyncio
async def test_response_scope_cancels_audio_and_closes_producers_after_consumer_error():
    state = {"closed": False, "audio_cancelled": False}

    class Producers:
        async def close(self):
            state["closed"] = True

    async def cancel_audio():
        state["audio_cancelled"] = True

    with pytest.raises(RuntimeError, match="consumer failed"):
        async with stream_response_scope(Producers(), cancel_audio):
            raise RuntimeError("consumer failed")

    assert state == {"closed": True, "audio_cancelled": True}


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


@pytest.mark.asyncio
async def test_stream_producer_group_cancels_workers_and_closes_tts_session():
    queue = asyncio.Queue()
    started = asyncio.Event()
    cleaned = asyncio.Event()
    closed = asyncio.Event()
    connected = asyncio.Event()

    class Session:
        async def connect(self):
            connected.set()

        async def receive(self, timeout=None):
            del timeout
            await asyncio.Event().wait()

        async def close(self):
            closed.set()

    async def source():
        started.set()
        try:
            await asyncio.Event().wait()
            yield None
        finally:
            cleaned.set()

    producers = StreamProducerGroup(queue)
    producers.start_llm(source())
    producers.start_tts(Session(), asyncio.Event())
    await started.wait()
    await connected.wait()
    await producers.close()

    assert cleaned.is_set()
    assert closed.is_set()
