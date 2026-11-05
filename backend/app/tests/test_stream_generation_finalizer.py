from app.services.qa.stream_generation_finalizer import finalize_stream_generation


def test_degraded_faq_finalization_pairs_authoritative_answer_with_uncacheable_policy():
    result = finalize_stream_generation(
        generated_answer="降级生成文本",
        finish_reason="fallback_provider_error",
        faq_documents_present=True,
        cache_allowed=True,
        llm_hit_level="faq_exact_styled",
        fallback_hit_level="faq_exact_styled_llm_fallback",
        llm_provider="primary",
        faq_answer="官方 FAQ 答案",
        persona="child",
        faq_sources=[{"title": "官方 FAQ"}],
    )

    assert result.answer != "降级生成文本"
    assert "官方 FAQ" in result.answer
    assert result.policy.degraded is True
    assert result.policy.should_cache is False
    assert result.policy.hit_level == "faq_exact_styled_llm_fallback"


def test_interrupted_rag_finalization_keeps_partial_answer_and_marks_incomplete():
    result = finalize_stream_generation(
        generated_answer="部分检索回答",
        finish_reason="interrupted_network",
        faq_documents_present=False,
        cache_allowed=True,
        llm_hit_level="rag",
        fallback_hit_level="rag_llm_fallback",
        llm_provider="primary",
        faq_answer="",
        persona="adult",
        faq_sources=[],
    )

    assert result.answer == "部分检索回答"
    assert result.policy.incomplete is True
    assert result.policy.completion == "incomplete"
    assert result.policy.should_cache is False
