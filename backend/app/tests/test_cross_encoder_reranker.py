from __future__ import annotations

import pytest

from app.services.rag.base import RetrievedDocument
from app.services.rag.cross_encoder_reranker import CrossEncoderReranker


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[dict] = []

    def predict(self, pairs, **kwargs):
        self.calls.append({"pairs": pairs, **kwargs})
        return self.scores


def test_cross_encoder_reranks_with_full_content() -> None:
    model = FakeCrossEncoder([0.2, 0.9, 0.4])
    reranker = CrossEncoderReranker(model=model, batch_size=4)
    documents = [
        RetrievedDocument(title="A", content="full A", snippet="short A"),
        RetrievedDocument(title="B", content="full B", snippet="short B"),
        RetrievedDocument(title="C", content="full C", snippet="short C"),
    ]

    results = reranker.rerank("query", documents, top_k=2)

    assert [item.document.title for item in results] == ["B", "C"]
    assert [item.score for item in results] == [0.9, 0.4]
    assert model.calls[0]["pairs"] == [
        ("query", "full A"),
        ("query", "full B"),
        ("query", "full C"),
    ]
    assert model.calls[0]["batch_size"] == 4
    assert model.calls[0]["show_progress_bar"] is False


def test_cross_encoder_uses_snippet_only_when_content_is_empty() -> None:
    model = FakeCrossEncoder([1.0])
    reranker = CrossEncoderReranker(model=model)

    reranker.rerank("query", [RetrievedDocument(title="A", snippet="fallback text")])

    assert model.calls[0]["pairs"] == [("query", "fallback text")]


def test_cross_encoder_handles_empty_input_and_invalid_score_shape() -> None:
    model = FakeCrossEncoder([])
    reranker = CrossEncoderReranker(model=model)

    assert reranker.rerank("query", [], top_k=5) == []
    assert reranker.rerank("query", [RetrievedDocument(title="A")], top_k=0) == []

    model.scores = [[0.1, 0.9]]
    with pytest.raises(RuntimeError, match="one relevance score"):
        reranker.rerank("query", [RetrievedDocument(title="A", content="text")])
