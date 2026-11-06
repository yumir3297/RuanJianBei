from app.services.qa.stream_terminal_policy import resolve_terminal_policy


def test_fallback_generation_uses_fallback_metadata_and_disables_cache():
    result = resolve_terminal_policy(
        finish_reason="fallback_provider_error",
        faq_documents_present=True,
        cache_allowed=True,
        llm_hit_level="faq_exact_styled",
        fallback_hit_level="faq_exact_styled_llm_fallback",
        llm_provider="primary",
    )

    assert result.degraded is True
    assert result.hit_level == "faq_exact_styled_llm_fallback"
    assert result.provider == "evidence_fallback"
    assert result.should_cache is False
    assert result.incomplete is False


def test_interrupted_non_faq_generation_is_incomplete_but_faq_is_complete():
    interrupted = resolve_terminal_policy(
        finish_reason="interrupted_network",
        faq_documents_present=False,
        cache_allowed=True,
        llm_hit_level="rag",
        fallback_hit_level="rag_llm_fallback",
        llm_provider="primary",
    )
    faq = resolve_terminal_policy(
        finish_reason="interrupted_network",
        faq_documents_present=True,
        cache_allowed=True,
        llm_hit_level="faq_restyle",
        fallback_hit_level="faq_restyle_llm_fallback",
        llm_provider="primary",
    )

    assert interrupted.incomplete is True
    assert interrupted.completion == "incomplete"
    assert faq.incomplete is False
    assert faq.completion == "complete"
