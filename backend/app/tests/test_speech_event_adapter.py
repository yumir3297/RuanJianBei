from app.services.qa.speech_event_adapter import (
    build_audio_event,
    handle_streaming_tts_event,
)
from app.services.tts.streaming import StreamingTTSEvent


def test_audio_event_uses_duration_floor_and_viseme_timeline_builder():
    event = build_audio_event(
        "你好",
        "YXVkaW8=",
        100,
        "stub",
        viseme_timeline_builder=lambda text, duration: [
            {"start": 0, "end": duration, "text": text}
        ],
    )

    assert event.type == "audio"
    assert event.data["base64"] == "YXVkaW8="
    assert event.data["duration_ms"] == 800
    assert event.data["viseme_timeline"] == [
        {"start": 0, "end": 800, "text": "你好"}
    ]


def test_pcm_chunk_is_encoded_as_mono_16_bit_audio_event():
    events = handle_streaming_tts_event(
        StreamingTTSEvent(type="audio_chunk", data=b"\x00\x01", sample_rate=16000),
        avatar_emotion="speaking",
        word_viseme_timeline_builder=lambda words: [],
    )

    assert len(events) == 1
    assert events[0].type == "audio_chunk"
    assert events[0].data == {
        "base64": "AAE=", "sample_rate": 16000, "channels": 1, "bits": 16,
    }


def test_word_timestamp_event_preserves_subtitles_and_emits_viseme_timeline():
    words = [{"text": "梵", "begin_time": 10, "end_time": 120}]
    events = handle_streaming_tts_event(
        StreamingTTSEvent(type="word_timestamps", data={
            "words": words, "sentence_index": 2, "characters": 1,
        }),
        avatar_emotion="speaking",
        word_viseme_timeline_builder=lambda value: [
            {"start": value[0]["begin_time"], "end": value[0]["end_time"]}
        ],
    )

    assert len(events) == 1
    assert events[0].type == "audio_chunk"
    assert events[0].data["sentence_index"] == 2
    assert events[0].data["viseme_timeline"] == [{"start": 10, "end": 120}]
    assert events[0].data["word_timeline"] == [
        {"text": "梵", "begin_time": 10, "end_time": 120}
    ]


def test_sentence_begin_emits_avatar_event_with_request_emotion():
    events = handle_streaming_tts_event(
        StreamingTTSEvent(type="sentence_begin", data="欢迎游览"),
        avatar_emotion="happy",
        word_viseme_timeline_builder=lambda words: [],
    )

    assert len(events) == 1
    assert events[0].type == "avatar"
    assert events[0].data == {"viseme_text": "欢迎游览", "emotion": "happy"}
