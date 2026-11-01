import asyncio

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.parametrize("failure", ["embedding_model_unavailable", "faq_semantic_index_unavailable"])
def test_missing_model_or_semantic_index_allows_startup_but_is_not_ready(monkeypatch, tmp_path, failure):
    import main
    from app.api import chat
    from app.core.config import Settings
    from app.services.qa import runtime

    settings = Settings(model_cache_dir=str(tmp_path / "models"),
                        knowledge_upload_dir=str(tmp_path / "knowledge"),
                        ui_asset_upload_dir=str(tmp_path / "assets"),
                        ui_asset_manifest_path=str(tmp_path / "manifest.json"))
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "_run_migrations", lambda: None)

    async def noop(*args, **kwargs):
        return None

    async def worker(*args, **kwargs):
        await asyncio.Event().wait()

    for name in ("bootstrap_quick_topics", "bootstrap_avatar_configs", "bootstrap_sample_data",
                 "bootstrap_experience_demo_feedback", "close_cached_llm_service", "close_cached_vision_service"):
        monkeypatch.setattr(main, name, noop)
    monkeypatch.setattr(main, "run_publication_worker", worker)
    monkeypatch.setattr(main, "run_import_worker", worker)
    async def faq(_session, *, embedder=None, **_kwargs):
        if embedder is not None and failure == "faq_semantic_index_unavailable":
            raise RuntimeError("semantic index failed")
    monkeypatch.setattr(runtime, "get_runtime_faq_matcher", faq)
    monkeypatch.setattr(chat, "get_cached_reranker", lambda *args: None)

    def missing(*args):
        if failure == "embedding_model_unavailable":
            raise RuntimeError("embedding model unavailable")
        return object()
    monkeypatch.setattr(chat, "get_cached_embedder", missing)

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def execute(self, _query):
            class Result:
                def scalar_one(self): return 1
            return Result()
    monkeypatch.setattr(main, "AsyncSessionLocal", Session)

    async def scenario():
        app = main.create_app()
        async with main.lifespan(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/health")).status_code == 200
                ready = await client.get("/ready")
                assert ready.status_code == 503
                assert failure in ready.json()["failures"]
    asyncio.run(scenario())
