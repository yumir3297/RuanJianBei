from app.services.asr.base import ASRResult


def test_heuristic_confidence_never_triggers_automatic_submission():
    assert ASRResult(text="可能的转写", confidence=0.99, confidence_source="heuristic").needs_confirmation
    assert not ASRResult(text="已转写", confidence=0.99, confidence_source="provider").needs_confirmation
    assert ASRResult(text="", confidence=0.99, confidence_source="provider").needs_confirmation
