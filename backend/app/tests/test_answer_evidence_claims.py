"""Source availability must not be presented as verification or invented citations."""
import asyncio

import pytest

from app.core.config import Settings
from app.services.llm.openai_compatible import OpenAICompatibleLLMService
from app.services.qa.faq_matcher import FAQEntry, FAQMatchResult
from app.services.qa.pipeline import QAPipeline
from app.services.qa.answer_styler import polish_answer, no_evidence_reply
from app.services.qa.answer_fast_paths import resolve_faq_path
from app.services.rag.base import RetrievedDocument


@pytest.mark.parametrize("sources", [[], [{"evidence_id": "证据1"}], [{"evidence_id": ""}]])
def test_answer_without_generated_citations_is_not_relabelled_as_citing_sources(sources):
    answer = "当前景区有12345人，急救点在北门。"
    assert QAPipeline._ensure_inline_citations(answer, sources) == answer


def test_natural_generated_citation_is_preserved_without_appending_other_documents():
    answer = "文档描述为88米。[证据2]"
    sources = [{"evidence_id": "证据1"}, {"evidence_id": "证据2"}]
    assert QAPipeline._ensure_inline_citations(answer, sources) == answer


@pytest.mark.parametrize("sources", [[], ["游客笔记.txt"]])
def test_faq_wrapper_preserves_provided_source_without_inventing_official_status(sources):
    match = FAQMatchResult(is_hit=True, entry=FAQEntry(
        id="test", category="test", aliases=[], answer="资料内容", sources=sources,
    ))
    decision = resolve_faq_path(match, audience="child", persona="guide")
    assert decision is not None
    document = (decision.documents or [])[0]
    assert "官方" not in document.title
    assert "官方" not in document.source
    if sources:
        assert document.source == sources[0]
    assert document.content == match.answer


@pytest.mark.parametrize("has_evidence", [False, True])
def test_provider_fallback_distinguishes_retrieved_material_from_official_verification(has_evidence):
    async def scenario():
        service = OpenAICompatibleLLMService(Settings(_env_file=None, llm_provider="stub"))
        documents = [RetrievedDocument(title="笔记", content="描述", source="游客笔记.txt", score=1)] if has_evidence else []
        return [event async for event in service.stream_generate("介绍", documents)]
    events = asyncio.run(scenario())
    answer = "".join(event.text or "" for event in events if event.type == "content")
    assert "官方" not in answer
    assert ("[证据1]" in answer) is has_evidence


def test_faq_styling_never_promotes_unknown_source_to_official():
    for index in range(40):
        assert "官方" not in polish_answer(f"记录{index}。", "hanfu", [{"source": "游客笔记"}])
    assert "官方" not in no_evidence_reply("hanfu")
