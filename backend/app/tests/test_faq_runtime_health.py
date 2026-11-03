import asyncio

import pytest
from app.services.qa import runtime


def test_runtime_semantic_failure_and_recovery_are_reported(monkeypatch):
    class Matcher:
        entries = [object()]
        broken = True

        def ensure_semantic_index(self, _embedder, _threshold):
            if self.broken:
                raise RuntimeError("semantic failed")

    matcher = Matcher()
    monkeypatch.setattr(runtime, "_faq_matcher", matcher)
    monkeypatch.setattr(runtime, "_semantic_index_failed", False)

    async def scenario():
        try:
            await runtime.get_runtime_faq_matcher(None, embedder=object())
        except RuntimeError:
            pass
        assert runtime.faq_semantic_index_failed()
        matcher.broken = False
        await runtime.get_runtime_faq_matcher(None, embedder=object())
        assert not runtime.faq_semantic_index_failed()

    asyncio.run(scenario())


def test_reload_failure_remains_visible_until_a_successful_reload(monkeypatch):
    class Matcher:
        semantic_index = None
        broken = True

        async def reload(self, _session):
            if self.broken:
                raise RuntimeError("database unavailable")
            return 1.0

    matcher = Matcher()
    monkeypatch.setattr(runtime, "_faq_matcher", matcher)
    monkeypatch.setattr(runtime, "_faq_reload_failed", False, raising=False)
    monkeypatch.setattr(runtime, "FAQMatcher", lambda: matcher)

    async def scenario():
        with pytest.raises(RuntimeError):
            await runtime.reload_runtime_faq_matcher(None)
        assert runtime.faq_reload_failed()
        matcher.broken = False
        await runtime.reload_runtime_faq_matcher(None)
        assert not runtime.faq_reload_failed()

    asyncio.run(scenario())


def test_runtime_reload_failure_is_visible(monkeypatch):
    from types import SimpleNamespace
    class Matcher:
        semantic_index = None

        async def reload(self, _session):
            return 1.0

        def ensure_semantic_index(self, _embedder, _threshold):
            raise RuntimeError("semantic rebuild failed")

    old = Matcher()
    old.semantic_index = SimpleNamespace(embedder=object(), threshold=0.85)
    monkeypatch.setattr(runtime, "_faq_matcher", old)
    monkeypatch.setattr(runtime, "FAQMatcher", Matcher)
    monkeypatch.setattr(runtime, "_semantic_index_failed", False)

    async def scenario():
        try:
            await runtime.reload_runtime_faq_matcher(None)
        except RuntimeError:
            pass
        assert runtime.faq_semantic_index_failed()

    asyncio.run(scenario())


def test_epoch_refresh_semantic_failure_keeps_new_exact_matcher_available(monkeypatch):
    from types import SimpleNamespace

    class Visibility:
        def __init__(self, _session): pass
        async def read_epoch(self): return 2

    class Candidate:
        entries = ["new"]
        semantic_index = None
        async def reload(self, _session): return 1.0
        def ensure_semantic_index(self, *_args): raise RuntimeError("semantic unavailable")

    old = SimpleNamespace(entries=["old"], knowledge_epoch=1,
                          semantic_index=SimpleNamespace(embedder=object(), threshold=0.85))
    monkeypatch.setattr(runtime, "_faq_matcher", old)
    monkeypatch.setattr(runtime, "FAQMatcher", Candidate)
    monkeypatch.setattr(runtime, "VisibilityService", Visibility)
    monkeypatch.setattr(runtime, "_faq_reload_failed", False)
    monkeypatch.setattr(runtime, "_semantic_index_failed", False)

    async def scenario():
        result = await runtime.get_runtime_faq_matcher(object())
        assert result is not old
        assert result.entries == ["new"] and result.knowledge_epoch == 2
        assert runtime.faq_semantic_index_failed()
        assert runtime.faq_reload_failed()
    asyncio.run(scenario())
