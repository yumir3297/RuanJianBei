from __future__ import annotations

from eval.metrics.latency import summarize_latency
from eval.metrics.retrieval import hit_at_k, mean_reciprocal_rank, recall_at_k, reciprocal_rank


def test_retrieval_metrics() -> None:
    relevant = {"target"}
    retrieved = ["other", "target", "third"]

    assert recall_at_k(relevant, retrieved, 1) == 0.0
    assert recall_at_k(relevant, retrieved, 2) == 1.0
    assert hit_at_k(relevant, retrieved, 1) == 0.0
    assert hit_at_k(relevant, retrieved, 2) == 1.0
    assert reciprocal_rank(relevant, retrieved) == 0.5
    assert mean_reciprocal_rank([1.0, 0.5, 0.0]) == 0.5


def test_latency_summary_uses_nearest_rank_percentiles() -> None:
    summary = summarize_latency([10, 20, 30, 40])

    assert summary == {
        "count": 4,
        "avg_ms": 25.0,
        "p50_ms": 20.0,
        "p95_ms": 40.0,
        "min_ms": 10.0,
        "max_ms": 40.0,
    }


def test_latency_summary_handles_empty_input() -> None:
    assert summarize_latency([])["count"] == 0
