import asyncio

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_events import StreamEvent


def test_queued_stream_events_preserves_batch_order_and_notifies_after_publish():
    async def run():
        events = QueuedStreamEvents()
        observed = []

        async def notify():
            observed.extend(events.drain())

        batch = [StreamEvent(type="avatar"), StreamEvent(type="audio")]
        await events.publish(batch, notify=notify)

        return observed, events.drain()

    observed, remaining = asyncio.run(run())
    assert [event.type for event in observed] == ["avatar", "audio"]
    assert remaining == ()


def test_queued_stream_events_drains_fifo_and_clears_buffer():
    events = QueuedStreamEvents()
    asyncio.run(events.publish([StreamEvent(type="text"), StreamEvent(type="done")]))

    assert [event.type for event in events.drain()] == ["text", "done"]
    assert events.drain() == ()
