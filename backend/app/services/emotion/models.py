from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class EmotionLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    DISSATISFIED = "dissatisfied"
    ANXIOUS = "anxious"
    URGENT = "urgent"


@dataclass(slots=True)
class EmotionSignal:
    label: EmotionLabel
    confidence: float
    intensity: float
    source: str
    evidence: tuple[str, ...] = ()
    available: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class FusedEmotion:
    label: EmotionLabel
    confidence: float
    intensity: float
    modalities: tuple[str, ...]
    conflict: bool = False
    signals: list[EmotionSignal] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "label": self.label.value,
            "confidence": self.confidence,
            "intensity": self.intensity,
            "modalities": list(self.modalities),
            "conflict": self.conflict,
            "signals": [signal.to_dict() for signal in self.signals],
        }
