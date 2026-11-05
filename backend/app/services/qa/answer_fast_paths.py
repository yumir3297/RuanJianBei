from __future__ import annotations

from dataclasses import dataclass

from app.services.llm.prompt_builder import get_audience_style
from app.services.qa.answer_styler import polish_answer
from app.services.qa.faq_matcher import FAQMatchResult
from app.services.rag.base import RetrievedDocument

_SCHEDULE_TERMS = (
    "开放时间", "营业时间", "演出时间", "什么时候开放", "几点开放", "几点开门", "几点关门",
)
_TICKET_TERMS = ("门票价格", "门票多少钱", "票价", "半价票", "免费入园")


@dataclass(slots=True)
class FAQPathDecision:
    answer: str | None
    source_answer: str
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
            source_answer=match.answer,
            sources=sources,
            documents=[document],
            hit_level=f"faq_{match.level}_styled",
        )

    return FAQPathDecision(
        answer=polish_answer(match.answer, persona, sources),
        source_answer=match.answer,
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


def resolve_unverified_schedule_answer(query: str) -> str | None:
    if not any(term in query for term in _SCHEDULE_TERMS):
        return None
    return "目前无法核实最新开放或演出时间，请以景区当日官方公告或现场咨询为准。"


def resolve_ticket_answer(query: str) -> str | None:
    ticket_discount = "优惠政策" in query and any(term in query for term in ("门票", "购票", "票务"))
    if not ticket_discount and not any(term in query for term in _TICKET_TERMS):
        return None
    return "目前无法核实最新票价和优惠条件，请以相关官方票务信息或现场咨询为准。"
