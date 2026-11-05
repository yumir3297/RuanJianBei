from dataclasses import dataclass

from app.services.qa.stream_finalization import resolve_final_answer
from app.services.qa.stream_terminal_policy import (
    StreamTerminalPolicy,
    resolve_terminal_policy,
)


@dataclass(frozen=True)
class FinalizedStreamGeneration:
    answer: str
    policy: StreamTerminalPolicy


def finalize_stream_generation(
    *,
    generated_answer: str,
    finish_reason: str | None,
    faq_documents_present: bool,
    cache_allowed: bool,
    llm_hit_level: str,
    fallback_hit_level: str,
    llm_provider: str,
    faq_answer: str,
    persona: str,
    faq_sources: list[dict],
) -> FinalizedStreamGeneration:
    """Resolve the canonical answer and its terminal metadata as one decision."""
    policy = resolve_terminal_policy(
        finish_reason=finish_reason,
        faq_documents_present=faq_documents_present,
        cache_allowed=cache_allowed,
        llm_hit_level=llm_hit_level,
        fallback_hit_level=fallback_hit_level,
        llm_provider=llm_provider,
    )
    answer = resolve_final_answer(
        generated_answer=generated_answer,
        degraded=policy.degraded,
        faq_documents_present=faq_documents_present,
        faq_answer=faq_answer,
        persona=persona,
        faq_sources=faq_sources,
    )
    return FinalizedStreamGeneration(answer=answer, policy=policy)
