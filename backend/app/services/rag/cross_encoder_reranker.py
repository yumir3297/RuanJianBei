from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from app.core.exceptions import AppError
from app.services.rag.base import RetrievedDocument
from app.services.rag.reranker import Reranker, RerankResult


class CrossEncoderReranker(Reranker):
    mode_name = "cross_encoder"

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        cache_dir: Path | None = None,
        batch_size: int = 8,
        max_length: int = 512,
        *,
        model: Any | None = None,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.batch_size = max(batch_size, 1)
        self.max_length = max(max_length, 1)

        if model is not None:
            self._model = model
            return

        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise AppError(
                "sentence-transformers is not installed. Install it before enabling CrossEncoder reranking.",
                error_code="reranker_dependency_missing",
                status_code=503,
            ) from exc

        self._model = CrossEncoder(
            model_name,
            cache_folder=str(self.cache_dir) if self.cache_dir is not None else None,
            local_files_only=local_files_only,
            max_length=self.max_length,
        )

    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[RerankResult]:
        if not documents or top_k <= 0:
            return []

        pairs = [(query, self._document_text(document)) for document in documents]
        raw_scores = self._model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        scores = self._normalize_scores(raw_scores)
        if len(scores) != len(documents):
            raise RuntimeError(
                f"CrossEncoder returned {len(scores)} scores for {len(documents)} documents."
            )

        ranked = sorted(
            zip(documents, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            RerankResult(document=document, score=score)
            for document, score in ranked[:top_k]
        ]

    @staticmethod
    def _document_text(document: RetrievedDocument) -> str:
        return document.content or document.snippet

    @classmethod
    def _normalize_scores(cls, raw_scores: Any) -> list[float]:
        if hasattr(raw_scores, "tolist"):
            raw_scores = raw_scores.tolist()
        if not isinstance(raw_scores, Sequence) or isinstance(raw_scores, (str, bytes)):
            raw_scores = [raw_scores]
        return [cls._score_to_float(score) for score in raw_scores]

    @classmethod
    def _score_to_float(cls, score: Any) -> float:
        if hasattr(score, "item"):
            score = score.item()
        if isinstance(score, Sequence) and not isinstance(score, (str, bytes)):
            if len(score) != 1:
                raise RuntimeError("CrossEncoder must return one relevance score per document.")
            return cls._score_to_float(score[0])
        return float(score)
