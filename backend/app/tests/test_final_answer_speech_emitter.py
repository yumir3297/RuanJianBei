import asyncio
from types import SimpleNamespace

from app.services.qa.final_answer_speech_emitter import FinalAnswerSpeechEmitter
from app.services.qa.stream_events import StreamEvent
from app.services.tts.base import TTSAudio


class RecordingTTS:
    def __init__(self):
        self.texts = []

    async def synthesize(self, text):
        self.texts.append(text)
        return TTSAudio(base64_audio="encoded", duration_ms=1200, provider="test")


class RecordingAvatar:
    def __init__(self):
        self.texts = []

    async def drive(self, text):
        self.texts.append(text)
        return SimpleNamespace(viseme_text=f"mouth:{text}", action="wave")


def _run(coro):
    return asyncio.run(coro)


def test_final_speech_emits_avatar_then_audio_after_parallel_rendering():
    tts = RecordingTTS()
    avatar = RecordingAvatar()
    emitter = FinalAnswerSpeechEmitter(
        tts_service=tts,
        avatar_service=avatar,
        audio_event_builder=lambda text, base64_audio, duration_ms, provider: StreamEvent(
            "audio",
            {"text": text, "base64": base64_audio, "duration_ms": duration_ms, "provider": provider},
        ),
        emotion_resolver=lambda hit_level, source_count: "happy",
        epoch_is_current=lambda expected_epoch: asyncio.sleep(0, result=True),
    )

    async def render():
        return await emitter.render(
            answer="有官方资料支持。", hit_level="faq_attraction", sources=[{"id": "s1"}], expected_epoch=7
        )

    events = _run(render())

    assert [event.type for event in events] == ["avatar", "audio"]
    assert events[0].data == {"viseme_text": "mouth:有官方资料支持。", "emotion": "happy", "action": "wave"}
    assert events[1].data["text"] == "有官方资料支持。"
    assert tts.texts == avatar.texts == ["有官方资料支持。"]


def test_long_faq_uses_short_speech_summary_at_sentence_boundary():
    tts = RecordingTTS()
    avatar = RecordingAvatar()
    emitter = FinalAnswerSpeechEmitter(
        tts_service=tts,
        avatar_service=avatar,
        audio_event_builder=lambda *args: StreamEvent("audio", {"text": args[0]}),
        emotion_resolver=lambda *_: "happy",
        epoch_is_current=lambda _: asyncio.sleep(0, result=True),
    )
    answer = "甲" * 90 + "。" + "乙" * 100

    _run(emitter.render(answer=answer, hit_level="faq_attraction", sources=[], expected_epoch=None))

    assert tts.texts == ["甲" * 90 + "。"]
    assert avatar.texts == tts.texts


def test_epoch_change_after_render_suppresses_stale_speech_events():
    tts = RecordingTTS()
    avatar = RecordingAvatar()
    emitter = FinalAnswerSpeechEmitter(
        tts_service=tts,
        avatar_service=avatar,
        audio_event_builder=lambda *args: StreamEvent("audio", {}),
        emotion_resolver=lambda *_: "neutral",
        epoch_is_current=lambda _: asyncio.sleep(0, result=False),
    )

    events = _run(
        emitter.render(answer="说明。", hit_level="cache", sources=[], expected_epoch=4)
    )

    assert [event.type for event in events] == ["error"]
    assert events[0].data["message"] == "知识内容已更新，已停止继续输出。"
