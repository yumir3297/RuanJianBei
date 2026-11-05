import asyncio
from types import SimpleNamespace

import pytest

from app.services.qa.faq_matcher import FAQEntry, FAQMatcher


def _resolver_type():
    from app.services.qa.answer_knowledge_path_resolver import AnswerKnowledgePathResolver

    return AnswerKnowledgePathResolver


class RecordingCache:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    async def get(self, key, *, epoch=None):
        self.calls.append((key, epoch))
        return self.answer


def _matcher(answer=None):
    matcher = FAQMatcher()
    if answer is not None:
        matcher.add([FAQEntry("faq-1", "general", ["景区介绍"], answer, ["官方资料"])])
    return matcher


@pytest.mark.asyncio
async def test_direct_faq_answer_stops_before_shared_cache_lookup():
    cache = RecordingCache()
    resolver = _resolver_type()(faq_matcher=_matcher("这里是景区介绍。"), cache=cache)

    result = await resolver.resolve(
        normalized_query="景区介绍",
        audience=None,
        persona="guide",
        vision_present=False,
        scoped_attraction=False,
        memory_prompt=None,
        neutral=True,
        cache_key="key-1",
        epoch=4,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )

    assert result.faq_path.answer is not None
    assert result.cache_allowed is None
    assert result.cached_answer is None
    assert cache.calls == []


@pytest.mark.asyncio
async def test_faq_rewrite_evidence_and_scoped_cache_result_keep_both_paths():
    cache = RecordingCache(SimpleNamespace(answer="cache hit", sources=[]))
    resolver = _resolver_type()(faq_matcher=_matcher("权威 FAQ 内容。"), cache=cache)

    result = await resolver.resolve(
        normalized_query="景区介绍",
        audience="child",
        persona="guide",
        vision_present=False,
        scoped_attraction=False,
        memory_prompt=None,
        neutral=True,
        cache_key="child-key",
        epoch=9,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )

    assert result.faq_path.answer is None
    assert result.faq_path.source_answer == "权威 FAQ 内容。"
    assert result.faq_path.documents
    assert result.cache_allowed is True
    assert result.cached_answer.answer == "根据现有资料记载—— cache hit"
    assert cache.calls == [("child-key", 9)]


@pytest.mark.asyncio
async def test_vision_or_personalized_memory_prevents_cache_read_and_faq_match():
    class MatcherThatMustNotRun:
        def match(self, query):
            raise AssertionError("vision questions must bypass unbound FAQ entries")

    cache = RecordingCache(SimpleNamespace(answer="must not leak", sources=[]))
    resolver = _resolver_type()(faq_matcher=MatcherThatMustNotRun(), cache=cache)

    result = await resolver.resolve(
        normalized_query="景区介绍",
        audience=None,
        persona="guide",
        vision_present=True,
        scoped_attraction=False,
        memory_prompt="游客记忆",
        neutral=True,
        cache_key="private-key",
        epoch=2,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )

    assert result.faq_path is None
    assert result.cache_allowed is False
    assert result.cached_answer is None
    assert cache.calls == []
