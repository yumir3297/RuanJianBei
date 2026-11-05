import pytest

from app.services.qa.audio_event_delivery import AudioEventDelivery
from app.services.qa.stream_events import StreamEvent


@pytest.mark.asyncio
async def test_audio_delivery_preserves_fifo_events_and_does_not_cancel_on_success():
    class Drainer:
        visibility_changed = False

        async def events(self):
            yield StreamEvent("avatar", {"viseme_text": "a"})
            yield StreamEvent("audio", {"text": "one"})

    cancelled = False

    async def cancel_audio():
        nonlocal cancelled
        cancelled = True

    delivery = AudioEventDelivery(Drainer(), cancel_audio)
    events = [event async for event in delivery.events()]

    assert [event.type for event in events] == ["avatar", "audio"]
    assert cancelled is False
    assert delivery.visibility_changed is False


@pytest.mark.asyncio
async def test_audio_delivery_cancels_remaining_audio_when_consumer_fails():
    class Drainer:
        visibility_changed = False

        async def events(self):
            yield StreamEvent("audio", {"text": "partial"})
            raise RuntimeError("drain failed")

    cancelled = False

    async def cancel_audio():
        nonlocal cancelled
        cancelled = True

    delivery = AudioEventDelivery(Drainer(), cancel_audio)
    with pytest.raises(RuntimeError, match="drain failed"):
        _ = [event async for event in delivery.events()]

    assert cancelled is True


@pytest.mark.asyncio
async def test_audio_delivery_emits_epoch_error_after_withholding_stale_events():
    class Drainer:
        visibility_changed = True

        async def events(self):
            yield StreamEvent("avatar", {})

    async def cancel_audio():
        raise AssertionError("epoch fence is handled by the drainer")

    delivery = AudioEventDelivery(Drainer(), cancel_audio)
    events = [event async for event in delivery.events()]

    assert [event.type for event in events] == ["avatar", "error"]
    assert events[-1].data["message"] == "知识内容已更新，已停止继续输出。"
    assert delivery.visibility_changed is True
