from app.api.insights import _hit_level_label


def test_existing_levels_are_unchanged():
    assert _hit_level_label(None) == "未分类"
    assert _hit_level_label("faq_exact") == "FAQ 精确匹配"
    assert _hit_level_label("faq_semantic") == "FAQ 语义匹配"
    assert _hit_level_label("cache") == "缓存命中"
    assert _hit_level_label("rag") == "RAG 检索回答"
    assert _hit_level_label("rag_llm_fallback") == "RAG 大模型补全"
    assert _hit_level_label("custom_level") == "custom_level"


def test_audience_rewritten_faq_levels_are_labelled():
    assert _hit_level_label("faq_exact_styled") == "FAQ 精确匹配（按受众改写）"
    assert _hit_level_label("faq_fuzzy_styled") == "FAQ 模糊匹配（按受众改写）"
    assert _hit_level_label("faq_semantic_styled") == "FAQ 语义匹配（按受众改写）"


def test_audience_rewritten_faq_fallback_is_labelled():
    assert (
        _hit_level_label("faq_exact_styled_llm_fallback")
        == "FAQ 精确匹配（按受众改写）·降级"
    )


def test_plain_rag_fallback_still_uses_the_generated_label():
    assert _hit_level_label("rag_evidence") == "RAG evidence"
