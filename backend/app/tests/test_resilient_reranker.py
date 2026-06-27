from __future__ import annotations

from app.services.rag.base import RetrievedDocument
from app.services.rag.reranker import Reranker, RerankResult
from app.services.rag.resilient_reranker import ResilientReranker


class FixedReranker(Reranker):
    def __init__(self, title: str, mode_name: str) -> None:
        self.title = title
        self.mode_name = mode_name

    def rerank(self, query, documents, top_k=5):
        del query, top_k
        document = next(item for item in documents if item.title == self.title)
        return [RerankResult(document=document, score=1.0)]


class FailingReranker(Reranker):
    def rerank(self, query, documents, top_k=5):
        del query, documents, top_k
        raise RuntimeError("reranker failed")


def documents() -> list[RetrievedDocument]:
    return [
        RetrievedDocument(title="A", score=0.8),
        RetrievedDocument(title="B", score=0.7),
    ]


def test_resilient_reranker_uses_primary() -> None:
    reranker = ResilientReranker(
        primary=FixedReranker("B", "cross_encoder"),
        fallback=FixedReranker("A", "bm25"),
    )

    results = reranker.rerank("query", documents())

    assert results[0].document.title == "B"
    assert reranker.last_mode == "cross_encoder"


def test_resilient_reranker_falls_back_to_bm25() -> None:
    reranker = ResilientReranker(
        primary=FailingReranker(),
        fallback=FixedReranker("B", "bm25"),
    )

    results = reranker.rerank("query", documents())

    assert results[0].document.title == "B"
    assert reranker.last_mode == "bm25_fallback"


def test_resilient_reranker_preserves_vector_order_when_all_rerankers_fail() -> None:
    reranker = ResilientReranker(
        primary=FailingReranker(),
        fallback=FailingReranker(),
    )

    results = reranker.rerank("query", documents(), top_k=1)

    assert results[0].document.title == "A"
    assert results[0].score == 0.8
    assert reranker.last_mode == "stable_order_fallback"
