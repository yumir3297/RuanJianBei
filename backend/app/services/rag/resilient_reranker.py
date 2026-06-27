from __future__ import annotations

import logging

from app.services.rag.base import RetrievedDocument
from app.services.rag.reranker import Reranker, RerankResult

logger = logging.getLogger(__name__)


class ResilientReranker(Reranker):
    def __init__(
        self,
        primary: Reranker | None,
        fallback: Reranker | None = None,
        stable_fallback: Reranker | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.stable_fallback = stable_fallback or Reranker()
        self.last_mode = "not_run"

    @property
    def mode_name(self) -> str:
        return self.last_mode

    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[RerankResult]:
        if not documents or top_k <= 0:
            self.last_mode = "empty"
            return []

        if self.primary is not None:
            try:
                results = self.primary.rerank(query, documents, top_k=top_k)
                self.last_mode = getattr(self.primary, "mode_name", "cross_encoder")
                return results
            except Exception:
                logger.exception("Primary reranker failed; attempting BM25 fallback.")

        if self.fallback is not None:
            try:
                results = self.fallback.rerank(query, documents, top_k=top_k)
                self.last_mode = "bm25_fallback"
                logger.warning("Using BM25 fallback reranker.")
                return results
            except Exception:
                logger.exception("BM25 fallback reranker failed; preserving vector order.")

        self.last_mode = "stable_order_fallback"
        logger.warning("Using stable-order fallback; no semantic reranker is available.")
        return self.stable_fallback.rerank(query, documents, top_k=top_k)
