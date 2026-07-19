from __future__ import annotations

from collections import defaultdict

from app.services.emotion.models import EmotionLabel, EmotionSignal, FusedEmotion


_AUDIO_LABELS = {
    "happy": EmotionLabel.POSITIVE,
    "positive": EmotionLabel.POSITIVE,
    "sad": EmotionLabel.ANXIOUS,
    "anxious": EmotionLabel.ANXIOUS,
    "angry": EmotionLabel.DISSATISFIED,
    "dissatisfied": EmotionLabel.DISSATISFIED,
    "neutral": EmotionLabel.NEUTRAL,
}


def audio_emotion_signal(
    emotion: str | None,
    confidence: float = 0.0,
    *,
    source: str = "sensevoice",
) -> EmotionSignal:
    normalized = str(emotion or "neutral").lower().replace("<|", "").replace("|>", "")
    label = _AUDIO_LABELS.get(normalized, EmotionLabel.NEUTRAL)
    available = confidence > 0
    return EmotionSignal(
        label=label,
        confidence=max(0.0, min(float(confidence), 1.0)),
        intensity=0.65 if label != EmotionLabel.NEUTRAL else 0.2,
        source=source,
        evidence=(normalized,) if available else (),
        available=available,
    )


class MultimodalEmotionFusion:
    """Confidence-gated late fusion for text semantics and speech emotion."""

    TEXT_WEIGHT = 0.65
    AUDIO_WEIGHT = 0.35

    def fuse(
        self,
        text_signal: EmotionSignal | None,
        audio_signal: EmotionSignal | None = None,
    ) -> FusedEmotion:
        signals = [signal for signal in (text_signal, audio_signal) if signal and signal.available]
        if not signals:
            return FusedEmotion(
                label=EmotionLabel.NEUTRAL,
                confidence=0.0,
                intensity=0.0,
                modalities=(),
            )

        urgent = next((signal for signal in signals if signal.label == EmotionLabel.URGENT), None)
        if urgent is not None:
            return FusedEmotion(
                label=EmotionLabel.URGENT,
                confidence=max(urgent.confidence, 0.95),
                intensity=max(urgent.intensity, 0.9),
                modalities=tuple(self._modality(signal) for signal in signals),
                conflict=False,
                signals=signals,
            )

        scores: dict[EmotionLabel, float] = defaultdict(float)
        intensity_total = 0.0
        weight_total = 0.0
        for signal in signals:
            weight = self.AUDIO_WEIGHT if self._modality(signal) == "audio" else self.TEXT_WEIGHT
            neutral_discount = 0.45 if signal.label == EmotionLabel.NEUTRAL else 1.0
            scores[signal.label] += weight * signal.confidence * neutral_discount
            intensity_total += weight * signal.intensity
            weight_total += weight

        label = max(scores, key=scores.get)
        non_neutral_labels = {signal.label for signal in signals if signal.label != EmotionLabel.NEUTRAL}
        conflict = len(non_neutral_labels) > 1
        score_total = sum(scores.values()) or 1.0
        confidence = scores[label] / score_total
        if len(signals) == 1:
            confidence = signals[0].confidence
        elif conflict:
            confidence *= 0.78

        return FusedEmotion(
            label=label,
            confidence=round(max(0.0, min(confidence, 1.0)), 3),
            intensity=round(intensity_total / max(weight_total, 0.001), 3),
            modalities=tuple(self._modality(signal) for signal in signals),
            conflict=conflict,
            signals=signals,
        )

    @staticmethod
    def _modality(signal: EmotionSignal) -> str:
        return "audio" if signal.source in {"sensevoice", "audio", "voice"} else "text"
