import asyncio
from types import SimpleNamespace

import pytest

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_events import StreamEvent
from app.services.tts.base import TTSAudio


def _publisher_type():
    from app.services.qa.queued_speech_publisher import QueuedSpeechPublisher

    return QueuedSpeechPublisher


@pytest.mark.asyncio
async def test_publisher_renders_then_waits_for_previous_audio_before_publishing():
    order = []

    class TTS:
        async def synthesize(self, text):
            order.append(("tts", text))
            return TTSAudio("encoded", 500, "test")

    class Avatar:
        async def drive(self, text):
            order.append(("avatar", text))
            return SimpleNamespace(viseme_text=f"mouth:{text}")

    class Queue(QueuedStreamEvents):
        async def publish(self, events, *, notify=None):
            order.append(("publish", [event.type for event in events]))
            await super().publish(events, notify=notify)

    publisher = _publisher_type()(
        tts_service=TTS(),
        avatar_service=Avatar(),
        audio_event_builder=lambda text, audio, duration, provider: StreamEvent(
            "audio", {"text": text, "audio": audio, "duration": duration, "provider": provider}
        ),
        emotion_resolver=lambda: "curious",
    )
    queue = Queue()

    async def previous_audio():
        await asyncio.sleep(0)
        order.append(("previous", "finished"))

    previous = asyncio.create_task(previous_audio())
    await publisher("你好。", queue, previous=previous)

    assert [entry[0] for entry in order] == ["tts", "avatar", "previous", "publish"]
    events = queue.drain()
    assert [event.type for event in events] == ["avatar", "audio"]
    assert events[0].data == {"viseme_text": "mouth:你好。", "emotion": "curious"}
    assert events[1].data == {
        "text": "你好。", "audio": "encoded", "duration": 500, "provider": "test"
    }


@pytest.mark.asyncio
async def test_publisher_keeps_text_stream_alive_when_sentence_tts_fails():
    class FailingTTS:
        async def synthesize(self, text):
            raise RuntimeError("provider unavailable")

    publisher = _publisher_type()(
        tts_service=FailingTTS(),
        avatar_service=SimpleNamespace(drive=lambda text: asyncio.sleep(0, result=SimpleNamespace(viseme_text=text))),
        audio_event_builder=lambda text, audio, duration, provider: StreamEvent(
            "audio", {"audio": audio, "duration": duration, "provider": provider}
        ),
        emotion_resolver=lambda: "neutral",
    )
    queue = QueuedStreamEvents()

    await publisher("仍可阅读。", queue)

    events = queue.drain()
    assert [event.type for event in events] == ["avatar", "audio"]
    assert events[1].data == {"audio": "", "duration": 0, "provider": "tts_unavailable"}


@pytest.mark.asyncio
async def test_publisher_propagates_cancellation_without_publishing_partial_events():
    class BlockingTTS:
        async def synthesize(self, text):
            await asyncio.Event().wait()

    publisher = _publisher_type()(
        tts_service=BlockingTTS(),
        avatar_service=SimpleNamespace(drive=lambda text: asyncio.sleep(0, result=SimpleNamespace(viseme_text=text))),
        audio_event_builder=lambda *args: StreamEvent("audio", {}),
        emotion_resolver=lambda: "neutral",
    )
    queue = QueuedStreamEvents()
    task = asyncio.create_task(publisher("取消时不发布。", queue))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert queue.drain() == ()
