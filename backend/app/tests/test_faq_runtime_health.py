import asyncio

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


def test_runtime_reload_failure_is_visible(monkeypatch):
    class Matcher:
        semantic_index = object()

        async def reload(self, _session):
            self.semantic_index = None
            raise RuntimeError("semantic rebuild failed")

    monkeypatch.setattr(runtime, "_faq_matcher", Matcher())
    monkeypatch.setattr(runtime, "_semantic_index_failed", False)

    async def scenario():
        try:
            await runtime.reload_runtime_faq_matcher(None)
        except RuntimeError:
            pass
        assert runtime.faq_semantic_index_failed()

    asyncio.run(scenario())
