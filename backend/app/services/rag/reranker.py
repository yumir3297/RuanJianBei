from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.base import RetrievedDocument


@dataclass(slots=True)
class RerankResult:
    document: RetrievedDocument
    score: float


class Reranker:
    mode_name = "stable_order"

    def rerank(self, query: str, documents: list[RetrievedDocument], top_k: int = 5) -> list[RerankResult]:
        """
        Stub implementation.

        The first version keeps the retrieval order stable and truncates the
        candidate set. A real reranker should score query against
        ``document.content`` and can replace this class without changing the
        pipeline contract.
        """
        del query
        if top_k <= 0:
            return []
        trimmed = documents[:top_k]
        return [RerankResult(document=doc, score=doc.score or 0.0) for doc in trimmed]
