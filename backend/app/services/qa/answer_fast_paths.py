from __future__ import annotations

from dataclasses import dataclass

from app.services.llm.prompt_builder import get_audience_style
from app.services.qa.answer_styler import polish_answer
from app.services.qa.faq_matcher import FAQMatchResult
from app.services.rag.base import RetrievedDocument


@dataclass(slots=True)
class FAQPathDecision:
    answer: str | None
    sources: list[dict]
    documents: list[RetrievedDocument] | None
    hit_level: str


def resolve_faq_path(
    match: FAQMatchResult | None,
    *,
    audience: str | None,
    persona: str,
) -> FAQPathDecision | None:
    """Resolve an FAQ hit into a zero-LLM answer or one evidence document."""
    if match is None or not match.is_hit:
        return None

    sources = [
        {
            "evidence_id": f"证据{index}",
            "title": "FAQ",
            "snippet": match.answer[:80],
            "source": source,
        }
        for index, source in enumerate(match.sources, start=1)
    ]
    if get_audience_style(audience):
        document = RetrievedDocument(
            title="常见问题资料",
            content=match.answer,
            snippet=match.answer,
            source="、".join(match.sources) or "常见问题资料（未标注来源）",
            score=1.0,
        )
        return FAQPathDecision(
            answer=None,
            sources=sources,
            documents=[document],
            hit_level=f"faq_{match.level}_styled",
        )

    return FAQPathDecision(
        answer=polish_answer(match.answer, persona, sources),
        sources=sources,
        documents=None,
        hit_level=f"faq_{match.level}",
    )


def shared_cache_allowed(
    *,
    vision_present: bool,
    memory_prompt: str | None,
    neutral: bool,
) -> bool:
    """Shared answers cannot cross personalized or multimodal request context."""
    return not vision_present and memory_prompt is None and neutral
