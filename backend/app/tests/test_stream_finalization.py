from app.services.qa.stream_finalization import resolve_final_answer


def test_degraded_faq_uses_the_authoritative_faq_answer_before_audio_and_persistence():
    answer = resolve_final_answer(
        generated_answer="证据降级回答",
        degraded=True,
        faq_documents_present=True,
        faq_answer="无锡马山官方 FAQ 答案",
        persona="child",
        faq_sources=[{"title": "官方 FAQ"}],
    )

    assert "无锡马山" in answer
    assert answer != "证据降级回答"


def test_non_degraded_or_non_faq_answer_keeps_the_generated_text():
    assert resolve_final_answer(
        generated_answer="已生成答案",
        degraded=False,
        faq_documents_present=True,
        faq_answer="FAQ 答案",
        persona="child",
        faq_sources=[],
    ) == "已生成答案"
    assert resolve_final_answer(
        generated_answer="部分答案",
        degraded=True,
        faq_documents_present=False,
        faq_answer="FAQ 答案",
        persona="adult",
        faq_sources=[],
    ) == "部分答案"
