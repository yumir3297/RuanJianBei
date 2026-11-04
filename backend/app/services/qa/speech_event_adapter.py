from __future__ import annotations

import base64
from collections.abc import Callable

from app.services.avatar.viseme import build_viseme_timeline as _build_viseme_timeline
from app.services.avatar.viseme import build_viseme_timeline_fallback
from app.services.qa.stream_events import StreamEvent


_PINYIN_FN = None
_PINYIN_CHECKED = False
_FINALS_STYLE = None


def _get_pinyin():
    global _PINYIN_FN, _PINYIN_CHECKED
    if not _PINYIN_CHECKED:
        _PINYIN_CHECKED = True
        try:
            from pypinyin import pinyin

            _PINYIN_FN = pinyin
        except ImportError:
            pass
    return _PINYIN_FN


def _get_finals_style():
    global _FINALS_STYLE
    if _FINALS_STYLE is None:
        try:
            from pypinyin import Style

            _FINALS_STYLE = Style.FINALS
        except ImportError:
            _FINALS_STYLE = -1
    return _FINALS_STYLE


def build_viseme_timeline(text: str, duration_ms: int) -> list[dict]:
    """Build text-based lip sync; fall back when pypinyin is unavailable."""
    pinyin_fn = _get_pinyin()
    if pinyin_fn is not None:
        return _build_viseme_timeline(text, duration_ms, pinyin_fn=pinyin_fn)
    return build_viseme_timeline_fallback(text, duration_ms)


def words_to_viseme_timeline(words: list[dict]) -> list[dict]:
    """Convert TTS word timestamps to viseme frames using Chinese finals."""
    from app.services.avatar.viseme import get_viseme_openness, get_viseme_roundness

    pinyin_fn = _get_pinyin()
    finals_style = _get_finals_style()
    timeline: list[dict] = []
    for word in words:
        char = word.get("text", "")
        begin = word.get("begin_time", 0)
        end = word.get("end_time", begin + 100)

        openness = 0.38
        roundness = 0.15
        if pinyin_fn is not None and finals_style is not None and finals_style >= 0 and char and not char.isspace():
            final = ""
            try:
                results = pinyin_fn(char, heteronym=False, style=finals_style)
                if results:
                    final = str(results[0][0]) if isinstance(results[0], list) else str(results[0])
            except Exception:
                pass
            if final:
                openness = get_viseme_openness(final)
                roundness = get_viseme_roundness(final)

        timeline.append({
            "start": begin,
            "end": end,
            "value": round(openness, 3),
            "form": round(roundness, 3),
        })
    return timeline


def build_audio_event(
    text: str,
    base64_audio: str,
    duration_ms: int,
    provider: str = "unknown",
    *,
    viseme_timeline_builder: Callable[[str, int], list[dict]] = build_viseme_timeline,
) -> StreamEvent:
    safe_duration = max(duration_ms, int(len(text.replace(" ", "")) * 180), 800)
    return StreamEvent(
        type="audio",
        data={
            "base64": base64_audio,
            "duration_ms": safe_duration,
            "text": text,
            "provider": provider,
            "viseme_timeline": viseme_timeline_builder(text, safe_duration),
        },
    )


def handle_streaming_tts_event(
    tts_event,
    *,
    avatar_emotion: str,
    word_viseme_timeline_builder: Callable[[list[dict]], list[dict]] = words_to_viseme_timeline,
) -> list[StreamEvent]:
    """Adapt a streaming TTS event to the chat SSE event contract."""
    results: list[StreamEvent] = []
    if tts_event.type == "audio_chunk":
        results.append(StreamEvent(type="audio_chunk", data={
            "base64": base64.b64encode(tts_event.data).decode("ascii"),
            "sample_rate": tts_event.sample_rate,
            "channels": 1,
            "bits": 16,
        }))
    elif tts_event.type == "word_timestamps":
        timestamp_data = tts_event.data if isinstance(tts_event.data, dict) else {"words": tts_event.data}
        raw_words = timestamp_data.get("words", [])
        viseme_timeline = word_viseme_timeline_builder(raw_words)
        if viseme_timeline:
            results.append(StreamEvent(type="audio_chunk", data={
                "viseme_timeline": viseme_timeline,
                "sentence_index": timestamp_data.get("sentence_index", 0),
                "word_timeline": [
                    {
                        "text": word.get("text", ""),
                        "begin_time": word.get("begin_time", 0),
                        "end_time": word.get("end_time", 0),
                    }
                    for word in raw_words
                ],
            }))
    elif tts_event.type == "sentence_begin":
        results.append(StreamEvent(type="avatar", data={
            "viseme_text": tts_event.data,
            "emotion": avatar_emotion,
        }))
    return results
