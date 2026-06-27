from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from app.api import chat as chat_module
from app.services.rag.embedder import SentenceTransformerEmbedder


class FakeSentenceTransformer:
    calls: list[tuple[str, dict]] = []

    def __init__(self, model_name: str, **kwargs) -> None:
        self.calls.append((model_name, kwargs))


def install_fake_sentence_transformers(monkeypatch) -> None:
    module = ModuleType("sentence_transformers")
    module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    FakeSentenceTransformer.calls.clear()


def test_embedder_forwards_local_files_only_and_keeps_default(monkeypatch, tmp_path: Path) -> None:
    install_fake_sentence_transformers(monkeypatch)

    SentenceTransformerEmbedder("offline-model", cache_dir=tmp_path, local_files_only=True)
    SentenceTransformerEmbedder("downloadable-model", cache_dir=tmp_path)

    assert FakeSentenceTransformer.calls == [
        (
            "offline-model",
            {"cache_folder": str(tmp_path), "local_files_only": True},
        ),
        (
            "downloadable-model",
            {"cache_folder": str(tmp_path), "local_files_only": False},
        ),
    ]


def test_chat_cached_embedder_always_uses_local_files(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path | None, bool]] = []

    class FakeEmbedder:
        def __init__(
            self,
            model_name: str,
            cache_dir: Path | None = None,
            *,
            local_files_only: bool = False,
        ) -> None:
            calls.append((model_name, cache_dir, local_files_only))

    monkeypatch.setattr(chat_module, "SentenceTransformerEmbedder", FakeEmbedder)
    chat_module.get_cached_embedder.cache_clear()
    try:
        chat_module.get_cached_embedder("offline-model", str(tmp_path))
    finally:
        chat_module.get_cached_embedder.cache_clear()

    assert calls == [("offline-model", tmp_path, True)]
