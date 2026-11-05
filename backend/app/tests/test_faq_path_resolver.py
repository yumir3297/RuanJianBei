from __future__ import annotations

from app.services.qa.faq_path_resolver import resolve_faq_path_for_request


class RecordingFAQMatcher:
    def __init__(self, result=None):
        self.result = result
        self.queries: list[str] = []

    def match(self, query: str):
        self.queries.append(query)
        return self.result


def test_faq_lookup_skips_vision_and_attraction_scoped_requests() -> None:
    matcher = RecordingFAQMatcher()

    vision_result = resolve_faq_path_for_request(
        matcher,
        "这个是什么",
        audience=None,
        persona="default",
        vision_present=True,
        scoped_attraction=False,
    )
    scoped_result = resolve_faq_path_for_request(
        matcher,
        "景区在哪里",
        audience=None,
        persona="default",
        vision_present=False,
        scoped_attraction=True,
    )

    assert vision_result is None
    assert scoped_result is None
    assert matcher.queries == []


def test_faq_lookup_matches_and_resolves_unscoped_text_request() -> None:
    from app.services.qa.faq_matcher import FAQEntry, FAQMatcher

    matcher = FAQMatcher()
    matcher.add([FAQEntry(
        id="location",
        category="practical",
        aliases=["景区在哪里"],
        answer="灵山胜境位于无锡马山。",
        sources=["景区官方公告"],
    )])

    decision = resolve_faq_path_for_request(
        matcher,
        "景区在哪里",
        audience=None,
        persona="default",
        vision_present=False,
        scoped_attraction=False,
    )

    assert decision is not None
    assert "灵山胜境位于无锡马山。" in decision.answer
    assert decision.source_answer == "灵山胜境位于无锡马山。"
    assert decision.documents is None
    assert decision.hit_level == "faq_exact"


def test_faq_lookup_returns_none_for_non_hit() -> None:
    matcher = RecordingFAQMatcher()

    decision = resolve_faq_path_for_request(
        matcher,
        "没有匹配的问题",
        audience=None,
        persona="default",
        vision_present=False,
        scoped_attraction=False,
    )

    assert decision is None
    assert matcher.queries == ["没有匹配的问题"]
