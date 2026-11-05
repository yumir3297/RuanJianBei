import asyncio

import pytest

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_completion import AudioTaskDrainer, StreamCompletionCoordinator
from app.services.qa.stream_events import StreamEvent


@pytest.mark.asyncio
async def test_completion_coordinator_drains_audio_before_cache_and_terminal_events():
    order = []

    class Turn:
        audio_visibility_changed = False

        async def final_audio_events(self, **kwargs):
            order.append("audio-start")
            yield StreamEvent(type="audio", data={"text": "回答"})
            order.append("audio-finished")

    async def epoch_is_current():
        order.append("epoch")
        return True

    async def cache_answer():
        order.append("cache")

    async def persist_answer():
        order.append("persist")
        return "log-1"

    coordinator = StreamCompletionCoordinator()
    events = [event async for event in coordinator.events(
        stream_turn=Turn(), answer="回答", faq_text_sent=False, incomplete=False,
        faq_documents_present=False, text_only=False, streaming_requested=False,
        epoch_is_current=epoch_is_current, cache_answer=cache_answer,
        persist_answer=persist_answer,
        followups_event=lambda: StreamEvent(type="followups"),
        done_event=lambda chat_log_id: StreamEvent(type="done", data={"id": chat_log_id}),
    )]

    assert [event.type for event in events] == ["audio", "text", "followups", "done"]
    assert order == [
        "audio-start", "audio-finished", "epoch", "cache", "epoch", "persist", "epoch"
    ]


@pytest.mark.asyncio
async def test_completion_coordinator_does_not_persist_if_epoch_changes_during_cache_write():
    calls = []
    epoch_checks = iter([True, False])

    class Turn:
        audio_visibility_changed = False

        async def final_audio_events(self, **kwargs):
            if False:
                yield StreamEvent(type="audio")

    async def epoch_is_current():
        return next(epoch_checks)

    async def cache_answer():
        calls.append("cache")

    async def persist_answer():
        calls.append("persist")
        return "log-stale"

    events = [event async for event in StreamCompletionCoordinator().events(
        stream_turn=Turn(), answer="基于旧知识的回答", faq_text_sent=False,
        incomplete=False, faq_documents_present=False, text_only=True,
        streaming_requested=False, epoch_is_current=epoch_is_current,
        cache_answer=cache_answer, persist_answer=persist_answer,
        followups_event=lambda: StreamEvent(type="followups"),
        done_event=lambda _: StreamEvent(type="done"),
    )]

    assert [event.type for event in events] == ["error"]
    assert calls == ["cache"]


@pytest.mark.asyncio
async def test_completion_coordinator_stops_when_audio_epoch_is_stale():
    calls = []

    class Turn:
        audio_visibility_changed = True

        async def final_audio_events(self, **kwargs):
            yield StreamEvent(type="error", data={"message": "stale"})

    async def forbidden():
        calls.append("side-effect")

    coordinator = StreamCompletionCoordinator()
    events = [event async for event in coordinator.events(
        stream_turn=Turn(), answer="回答", faq_text_sent=False, incomplete=False,
        faq_documents_present=False, text_only=False, streaming_requested=False,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
        cache_answer=forbidden, persist_answer=forbidden,
        followups_event=lambda: StreamEvent(type="followups"),
        done_event=lambda chat_log_id: StreamEvent(type="done"),
    )]

    assert [event.type for event in events] == ["error"]
    assert calls == []


@pytest.mark.asyncio
async def test_completion_coordinator_closes_audio_stream_and_cancels_tasks_on_client_close():
    state = {"audio_closed": False, "cancelled": False}

    class Turn:
        audio_visibility_changed = False

        async def final_audio_events(self, **kwargs):
            try:
                yield StreamEvent(type="audio")
                await asyncio.sleep(60)
            finally:
                state["audio_closed"] = True

        async def cancel_audio(self):
            state["cancelled"] = True

    async def forbidden():
        pytest.fail("client close must happen before cache and persistence")

    events = StreamCompletionCoordinator().events(
        stream_turn=Turn(), answer="回答", faq_text_sent=False, incomplete=False,
        faq_documents_present=False, text_only=False, streaming_requested=False,
        epoch_is_current=lambda: asyncio.sleep(0, result=True), cache_answer=forbidden,
        persist_answer=forbidden,
        followups_event=lambda: StreamEvent(type="followups"),
        done_event=lambda _: StreamEvent(type="done"),
    )

    assert (await anext(events)).type == "audio"
    await events.aclose()

    assert state == {"audio_closed": True, "cancelled": True}


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
