from __future__ import annotations

from app.services.qa.answer_fast_paths import FAQPathDecision, resolve_faq_path
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.guidematch_gate import structured_hard_rule, text_date_conflict
from difflib import SequenceMatcher


def resolve_faq_path_for_request(
    matcher: FAQMatcher,
    normalized_query: str,
    *,
    audience: str | None,
    persona: str,
    vision_present: bool,
    scoped_attraction: bool,
    guidematch_gate=None,
) -> FAQPathDecision | None:
    """Match and resolve the FAQ fast path when request evidence permits it.

    FAQ entries have no verifiable attraction binding, so image questions and
    attraction-scoped questions must continue through their evidence-aware paths.
    """
    if vision_present or scoped_attraction:
        return None

    match = matcher.match(normalized_query)
    if guidematch_gate is not None and match.is_hit and match.entry and match.level != "exact":
        aliases = [alias for alias in match.entry.aliases if alias.strip()]
        if not aliases:
            return None
        candidate = match.matched_alias or max(aliases, key=lambda alias: SequenceMatcher(None, matcher._normalize(normalized_query), matcher._normalize(alias)).ratio())
        try:
            # Only use entities and intent classes already established by the
            # existing FAQ index; do not invent metadata from unverified text.
            index = matcher.semantic_gate
            left_entity = index._find_entity(matcher._normalize(normalized_query))
            right_entity = index._find_entity(matcher._normalize(candidate))
            left_intent = index._classify_spot_intent(normalized_query) if left_entity else None
            right_intent = index._classify_spot_intent(candidate) if right_entity else None
            hard = structured_hard_rule(
                {"poi_id": left_entity, "target_id": left_intent},
                {"poi_id": right_entity, "target_id": right_intent},
            )
            if hard or text_date_conflict(normalized_query, candidate):
                return None
            if guidematch_gate.decide(normalized_query, candidate) != "reuse":
                return None
        except Exception:
            return None
    return resolve_faq_path(match, audience=audience, persona=persona)
