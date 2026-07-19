from app.services.emotion import (
    EmotionLabel,
    MultimodalEmotionFusion,
    TextEmotionAnalyzer,
    audio_emotion_signal,
)


def test_text_emotion_detects_scenic_service_intents() -> None:
    analyzer = TextEmotionAnalyzer()

    assert analyzer.analyze("\u8fd9\u91cc\u592a\u6f02\u4eae\u4e86\uff0c\u8c22\u8c22\u4f60\u7684\u4ecb\u7ecd\uff01").label == EmotionLabel.POSITIVE
    assert analyzer.analyze("\u4f60\u8bf4\u7684\u6211\u8fd8\u662f\u6ca1\u542c\u61c2\uff0c\u80fd\u7b80\u5355\u4e00\u70b9\u5417").label == EmotionLabel.CONFUSED
    assert analyzer.analyze("\u6392\u961f\u592a\u4e45\u4e86\uff0c\u4f53\u9a8c\u5f88\u5dee").label == EmotionLabel.DISSATISFIED
    assert analyzer.analyze("\u6211\u6709\u70b9\u5934\u6655\u4e0d\u8212\u670d").label == EmotionLabel.ANXIOUS


def test_urgent_text_overrides_audio_emotion() -> None:
    analyzer = TextEmotionAnalyzer()
    fusion = MultimodalEmotionFusion()
    text_signal = analyzer.analyze("\u6211\u7684\u5b69\u5b50\u627e\u4e0d\u5230\u4e86\uff0c\u5feb\u5e2e\u5e2e\u6211\uff01")
    audio_signal = audio_emotion_signal("happy", 0.9)

    result = fusion.fuse(text_signal, audio_signal)

    assert result.label == EmotionLabel.URGENT
    assert result.confidence >= 0.95
    assert result.conflict is False


def test_audio_can_refine_neutral_text_and_conflicts_are_marked() -> None:
    analyzer = TextEmotionAnalyzer()
    fusion = MultimodalEmotionFusion()

    angry_result = fusion.fuse(
        analyzer.analyze("\u8fd9\u4e2a\u8def\u7ebf\u662f\u8fd9\u6837\u7684\u5417"),
        audio_emotion_signal("angry", 0.9),
    )
    conflict_result = fusion.fuse(
        analyzer.analyze("\u8fd9\u91cc\u592a\u6f02\u4eae\u4e86"),
        audio_emotion_signal("angry", 0.9),
    )

    assert angry_result.label == EmotionLabel.DISSATISFIED
    assert angry_result.modalities == ("text", "audio")
    assert conflict_result.conflict is True
