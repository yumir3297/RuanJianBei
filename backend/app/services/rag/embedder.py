from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol, Sequence

from app.core.exceptions import AppError


class BaseEmbedder(Protocol):
    model_name: str

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple texts with the same vector space."""

    def embed(self, text: str) -> list[float]:
        """Embed one text."""


class SimpleEmbedder:
    """Deterministic test/dev embedder. Production RAG should use SentenceTransformerEmbedder."""

    model_name = "simple-dev-embedder"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [byte / 255 for byte in digest[:16]]


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str,
        cache_dir: Path | None = None,
        *,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise AppError(
                "sentence-transformers is not installed. Install it before building the RAG index.",
                error_code="rag_dependency_missing",
                status_code=503,
            ) from exc

        self._model = SentenceTransformer(
            model_name,
            cache_folder=str(self.cache_dir) if self.cache_dir is not None else None,
            local_files_only=local_files_only,
        )

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        if hasattr(vectors, "tolist"):
            return vectors.tolist()
        return [list(vector) for vector in vectors]

    def embed(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
