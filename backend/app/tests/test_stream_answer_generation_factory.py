from __future__ import annotations

from types import SimpleNamespace

from app.schemas.chat import ChatRequest
from app.services.qa.stream_answer_generation_factory import StreamAnswerGenerationFactory
from app.services.qa.stream_generation_run import StreamGenerationRun
from app.services.rag.base import RetrievedDocument


def test_generation_factory_binds_request_context_and_faq_finalization_policy() -> None:
    turn_factory = object()
    emotion_aware_query = lambda query: f"warm:{query}"
    epoch_is_current = lambda: None
    request = ChatRequest(
        query="景区在哪里",
        session_id="factory-test",
        persona="hanfu",
        text_only=True,
    )
    document = RetrievedDocument(title="FAQ", content="原文", source="官方")
    factory = StreamAnswerGenerationFactory(
        turn_factory=turn_factory,
        llm_provider_name="primary",
        emotion_aware_query=emotion_aware_query,
        epoch_is_current=epoch_is_current,
    )

    run = factory.build(
        request=request,
        documents=[document],
        audience="child",
        memory="游客喜欢建筑",
        confirmed_visual_title="灵山大佛",
        vision_context_present=True,
        faq_documents_present=True,
        cache_allowed=False,
        llm_hit_level="faq_exact_styled",
        fallback_hit_level="faq_exact_styled_llm_fallback",
        faq_answer="权威 FAQ 原文",
        faq_sources=[{"evidence_id": "证据1"}],
    )

    assert isinstance(run, StreamGenerationRun)
    assert run.turn_factory is turn_factory
    assert run.turn_kwargs == {
        "query": "景区在哪里",
        "documents": [document],
        "persona": "hanfu",
        "audience": "child",
        "memory": "游客喜欢建筑",
        "confirmed_visual_title": "灵山大佛",
        "vision_context_present": True,
        "faq_documents_present": True,
        "text_only": True,
        "epoch_is_current": epoch_is_current,
        "emotion_aware_query": emotion_aware_query,
    }
    assert run.finalization_kwargs == {
        "faq_documents_present": True,
        "cache_allowed": False,
        "llm_hit_level": "faq_exact_styled",
        "fallback_hit_level": "faq_exact_styled_llm_fallback",
        "llm_provider": "primary",
        "faq_answer": "权威 FAQ 原文",
        "persona": "hanfu",
        "faq_sources": [{"evidence_id": "证据1"}],
    }


def test_generation_factory_keeps_rag_requests_unpersonalized_when_context_is_empty() -> None:
    factory = StreamAnswerGenerationFactory(
        turn_factory="turn-factory",
        llm_provider_name="local-provider",
        emotion_aware_query=lambda query: query,
        epoch_is_current=lambda: None,
    )
    document = RetrievedDocument(title="资料", content="说明")

    run = factory.build(
        request=SimpleNamespace(query="怎么去", persona="adult", text_only=False),
        documents=[document],
        audience=None,
        memory=None,
        confirmed_visual_title=None,
        vision_context_present=False,
        faq_documents_present=False,
        cache_allowed=True,
        llm_hit_level="rag",
        fallback_hit_level="rag_llm_fallback",
        faq_answer="",
        faq_sources=[],
    )

    assert run.turn_kwargs["memory"] is None
    assert run.turn_kwargs["vision_context_present"] is False
    assert run.finalization_kwargs["faq_documents_present"] is False
    assert run.finalization_kwargs["cache_allowed"] is True
    assert run.finalization_kwargs["faq_answer"] == ""
