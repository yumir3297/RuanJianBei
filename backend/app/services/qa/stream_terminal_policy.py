from dataclasses import dataclass


@dataclass(frozen=True)
class StreamTerminalPolicy:
    degraded: bool
    incomplete: bool
    completion: str
    hit_level: str
    provider: str
    should_cache: bool


def resolve_terminal_policy(
    *,
    finish_reason: str | None,
    faq_documents_present: bool,
    cache_allowed: bool,
    llm_hit_level: str,
    fallback_hit_level: str,
    llm_provider: str,
) -> StreamTerminalPolicy:
    degraded = bool(
        finish_reason
        and (finish_reason.startswith("fallback_") or finish_reason.startswith("interrupted_"))
    )
    incomplete = bool(
        finish_reason and finish_reason.startswith("interrupted_") and not faq_documents_present
    )
    return StreamTerminalPolicy(
        degraded=degraded,
        incomplete=incomplete,
        completion="incomplete" if incomplete else "complete",
        hit_level=fallback_hit_level if degraded else llm_hit_level,
        provider="evidence_fallback" if degraded else llm_provider,
        should_cache=cache_allowed and not degraded,
    )
