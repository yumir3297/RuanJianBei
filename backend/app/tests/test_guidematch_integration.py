import asyncio

import pytest

from app.services.qa.answer_knowledge_path_resolver import AnswerKnowledgePathResolver
from app.services.qa.faq_matcher import FAQEntry, FAQMatcher
from app.services.qa.guidematch_gate import structured_hard_rule, text_date_conflict, load_gate


class Gate:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def decide(self, query, candidate):
        self.calls.append((query, candidate))
        return self.decision


class Cache:
    async def get(self, *args, **kwargs):
        raise AssertionError("gate rejection must not fall through to shared cache")


@pytest.mark.asyncio
@pytest.mark.parametrize("decision,expected", [("reuse", True), ("distinct", False), ("clarify", False)])
async def test_guidematch_controls_fuzzy_faq_and_blocks_cache(decision, expected):
    matcher = FAQMatcher()
    matcher.add([FAQEntry("one", "general", ["大佛在哪里"], "景点资料", ["来源"])])
    gate = Gate(decision)
    result = await AnswerKnowledgePathResolver(faq_matcher=matcher, cache=Cache(), guidematch_gate=gate).resolve(
        normalized_query="大佛在哪里呢", audience=None, persona="guide", vision_present=False,
        scoped_attraction=False, memory_prompt=None, neutral=True, cache_key="test", epoch=1,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )
    assert (result.faq_path is not None) is expected
    assert gate.calls == [("大佛在哪里呢", "大佛在哪里")]
    if not expected:
        assert result.cache_allowed is False


@pytest.mark.parametrize("field", ["poi_id", "target_id", "queried_date"])
def test_structured_conflict_and_one_sided_field(field):
    assert structured_hard_rule({field: "a"}, {field: "b"}) == "distinct"
    assert structured_hard_rule({field: "a"}, {}) == "clarify"
    assert structured_hard_rule({field: "a"}, {field: "a"}) is None


def test_text_dates_do_not_silently_reuse_different_days():
    assert text_date_conflict("今天几点开门", "明天几点开门")
    assert text_date_conflict("2026-11-12开放吗", "开放吗")
    assert not text_date_conflict("今天开放吗", "今天开门吗")


def test_missing_model_disables_nonexact_faq_reuse(tmp_path):
    gate = load_gate(str(tmp_path / "absent"), "cpu")
    assert gate.decide("query", "candidate") == "clarify"
    load_gate.cache_clear()


@pytest.mark.asyncio
async def test_known_cross_attraction_is_rejected_before_model():
    matcher = FAQMatcher()
    matcher.add([
        FAQEntry("one", "景点位置", ["灵山大佛在哪里"], "大佛位置", ["来源"]),
        FAQEntry("two", "景点位置", ["九龙灌浴在哪里"], "灌浴位置", ["来源"]),
    ])
    # Force the first FAQ as the fuzzy candidate to exercise the routing fence.
    from app.services.qa.faq_matcher import FAQMatchResult
    matcher.match = lambda query: FAQMatchResult(True, "fuzzy", matcher.entries[0])
    gate = Gate("reuse")
    result = await AnswerKnowledgePathResolver(faq_matcher=matcher, cache=Cache(), guidematch_gate=gate).resolve(
        normalized_query="九龙灌浴在哪里呢", audience=None, persona="guide", vision_present=False,
        scoped_attraction=False, memory_prompt=None, neutral=True, cache_key="test", epoch=1,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )
    assert result.faq_path is None
    assert gate.calls == []
