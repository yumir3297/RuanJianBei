from __future__ import annotations

from app.services.qa.answer_fast_paths import FAQPathDecision, resolve_faq_path
from app.services.qa.faq_matcher import FAQMatcher


def resolve_faq_path_for_request(
    matcher: FAQMatcher,
    normalized_query: str,
    *,
    audience: str | None,
    persona: str,
    vision_present: bool,
    scoped_attraction: bool,
) -> FAQPathDecision | None:
    """Match and resolve the FAQ fast path when request evidence permits it.

    FAQ entries have no verifiable attraction binding, so image questions and
    attraction-scoped questions must continue through their evidence-aware paths.
    """
    if vision_present or scoped_attraction:
        return None

    match = matcher.match(normalized_query)
    return resolve_faq_path(match, audience=audience, persona=persona)
