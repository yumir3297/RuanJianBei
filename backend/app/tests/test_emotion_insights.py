import json
from datetime import datetime
from types import SimpleNamespace

from app.services.insights import build_emotion_insights


def _log(log_id: int, fused: str, *, audio: str | None = None, conflict: bool = False):
    modalities = ["text", "audio"] if audio else ["text"]
    return SimpleNamespace(
        id=log_id,
        raw_query=f"query-{log_id}",
        input_mode="voice" if audio else "text",
        text_emotion=fused,
        audio_emotion=audio,
        fused_emotion=fused,
        emotion_confidence=0.82,
        emotion_conflict=conflict,
        emotion_modalities=json.dumps(modalities),
        response_strategy="safety_first" if fused == "urgent" else "neutral",
        created_at=datetime(2026, 7, 19, 9, log_id),
    )


def test_emotion_insights_summarizes_multimodal_attention_and_recent_records() -> None:
    logs = [
        _log(3, "urgent", audio="anxious", conflict=True),
        _log(2, "confused"),
        _log(1, "neutral"),
    ]

    result = build_emotion_insights(logs)

    assert result.total_analyzed == 3
    assert result.multimodal_count == 1
    assert result.conflict_count == 1
    assert result.attention_count == 2
    assert result.urgent_count == 1
    assert {item.emotion: item.count for item in result.distribution}["confused"] == 1
    assert result.recent[0].modalities == ["text", "audio"]
    assert result.recent[0].query == "query-3"


def test_emotion_insights_handles_empty_logs() -> None:
    result = build_emotion_insights([])

    assert result.total_analyzed == 0
    assert result.multimodal_count == 0
    assert all(item.ratio == 0 for item in result.distribution)
    assert result.recent == []
