import asyncio
from types import SimpleNamespace

from app.api import chat
from app.core.config import Settings


def test_pipeline_uses_new_exact_matcher_after_semantic_reload_failure(monkeypatch):
    old, new = object(), object()
    calls = []

    async def get_matcher(_session, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return old
        if kwargs.get("embedder") is not None:
            raise RuntimeError("semantic rebuild failed after publishing new exact matcher")
        return new

    monkeypatch.setattr(chat, "get_runtime_faq_matcher", get_matcher)
    monkeypatch.setattr(chat, "get_cached_embedder", lambda *_: object())
    monkeypatch.setattr(chat, "get_cached_vector_store", lambda *_: (_ for _ in ()).throw(RuntimeError("unavailable")))
    monkeypatch.setattr(chat, "get_cached_llm_service", lambda *_: object())
    monkeypatch.setattr(chat, "QAPipeline", lambda **kwargs: SimpleNamespace(**kwargs))
    pipeline = asyncio.run(chat.build_pipeline(object(), Settings()))
    assert pipeline.faq_matcher is new
