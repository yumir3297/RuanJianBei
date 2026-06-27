from __future__ import annotations

from app.services.rag.base import RetrievedDocument
from app.services.rag.bm25_reranker import BM25Reranker, tokenize_for_bm25


def test_bm25_tokenizer_contains_chinese_characters_and_bigrams() -> None:
    tokens = tokenize_for_bm25("灵山大佛 88M")

    assert "灵" in tokens
    assert "灵山" in tokens
    assert "大佛" in tokens
    assert "88m" in tokens


def test_bm25_order_changes_with_query() -> None:
    reranker = BM25Reranker()
    documents = [
        RetrievedDocument(title="大佛", content="灵山大佛 青铜佛像 高八十八米"),
        RetrievedDocument(title="梵宫", content="灵山梵宫 莲花穹顶 建筑艺术"),
        RetrievedDocument(title="餐饮", content="景区素斋 素面 餐饮服务"),
    ]

    architecture = reranker.rerank("莲花建筑", documents, top_k=3)
    dining = reranker.rerank("素斋餐饮", documents, top_k=3)

    assert architecture[0].document.title == "梵宫"
    assert dining[0].document.title == "餐饮"


def test_bm25_preserves_order_for_empty_query() -> None:
    reranker = BM25Reranker()
    documents = [
        RetrievedDocument(title="A", score=0.8),
        RetrievedDocument(title="B", score=0.7),
    ]

    results = reranker.rerank("", documents, top_k=1)

    assert results[0].document.title == "A"
    assert results[0].score == 0.8
