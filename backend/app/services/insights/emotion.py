from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.models.chat_log import ChatLog
from app.schemas.insights import EmotionDistributionItem, EmotionInsights, RecentEmotionItem


EMOTION_LABELS = {
    "positive": "积极",
    "neutral": "中性",
    "confused": "困惑",
    "dissatisfied": "不满",
    "anxious": "焦虑",
    "urgent": "紧急",
}
ATTENTION_EMOTIONS = {"confused", "dissatisfied", "anxious", "urgent"}


def _modalities(payload: str | list[Any] | None) -> list[str]:
    if isinstance(payload, list):
        return [str(item) for item in payload]
    try:
        parsed = json.loads(payload or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def build_emotion_insights(logs: list[ChatLog]) -> EmotionInsights:
    total = len(logs)
    distribution = Counter((log.fused_emotion or "neutral") for log in logs)
    multimodal_count = sum(
        1
        for log in logs
        if "audio" in _modalities(log.emotion_modalities) or log.audio_emotion
    )
    recent = [
        RecentEmotionItem(
            id=log.id,
            query=log.raw_query,
            input_mode=log.input_mode,
            text_emotion=log.text_emotion or "neutral",
            audio_emotion=log.audio_emotion,
            fused_emotion=log.fused_emotion or "neutral",
            confidence=round(float(log.emotion_confidence or 0), 3),
            conflict=bool(log.emotion_conflict),
            modalities=_modalities(log.emotion_modalities),
            response_strategy=log.response_strategy or "neutral",
            created_at=log.created_at,
        )
        for log in logs[:10]
    ]
    return EmotionInsights(
        total_analyzed=total,
        multimodal_count=multimodal_count,
        conflict_count=sum(1 for log in logs if log.emotion_conflict),
        attention_count=sum(1 for log in logs if log.fused_emotion in ATTENTION_EMOTIONS),
        urgent_count=distribution["urgent"],
        distribution=[
            EmotionDistributionItem(
                emotion=emotion,
                label=label,
                count=distribution[emotion],
                ratio=round(distribution[emotion] / total, 3) if total else 0,
            )
            for emotion, label in EMOTION_LABELS.items()
        ],
        recent=recent,
    )
