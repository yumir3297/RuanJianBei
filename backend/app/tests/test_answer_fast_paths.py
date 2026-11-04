from app.services.qa.faq_matcher import FAQEntry, FAQMatchResult
from app.services.qa.answer_fast_paths import resolve_faq_path, shared_cache_allowed


def _faq_result() -> FAQMatchResult:
    return FAQMatchResult(
        is_hit=True,
        level="exact",
        entry=FAQEntry(
            id="faq-location",
            category="practical",
            aliases=["景区在哪里"],
            answer="灵山胜境位于无锡马山。",
            sources=["景区官方公告"],
        ),
    )


def test_default_audience_faq_resolves_to_direct_answer_without_documents():
    decision = resolve_faq_path(_faq_result(), audience="adult", persona="guide")

    assert decision is not None
    assert decision.answer.endswith("灵山胜境位于无锡马山。")
    assert decision.documents is None
    assert decision.hit_level == "faq_exact"
    assert decision.sources == [{
        "evidence_id": "证据1",
        "title": "FAQ",
        "snippet": "灵山胜境位于无锡马山。",
        "source": "景区官方公告",
    }]


def test_child_audience_faq_resolves_to_one_source_document_for_restyling():
    decision = resolve_faq_path(_faq_result(), audience="child", persona="guide")

    assert decision is not None
    assert decision.answer is None
    assert len(decision.documents or []) == 1
    assert decision.documents[0].content == "灵山胜境位于无锡马山。"
    assert decision.hit_level == "faq_exact_styled"


def test_shared_cache_is_disabled_for_personalized_or_non_neutral_requests():
    assert shared_cache_allowed(vision_present=False, memory_prompt=None, neutral=True)
    assert not shared_cache_allowed(vision_present=True, memory_prompt=None, neutral=True)
    assert not shared_cache_allowed(vision_present=False, memory_prompt="游客偏好", neutral=True)
    assert not shared_cache_allowed(vision_present=False, memory_prompt=None, neutral=False)
