from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402
from app.services.rag.embedder import SentenceTransformerEmbedder  # noqa: E402
from app.services.rag.query_rewriter import QueryRewriter  # noqa: E402
from app.services.rag.vector_store import ChromaVectorStore  # noqa: E402
from eval.metrics.latency import summarize_latency  # noqa: E402
from eval.metrics.retrieval import hit_at_k, mean_reciprocal_rank, reciprocal_rank  # noqa: E402

TOP_K = 5
THRESHOLDS = {
    "recall_at_5": 0.90,
    "mrr": 0.75,
    "vector_p95_ms": 300.0,
}


def load_cases(testset_path: Path) -> list[dict[str, Any]]:
    cases = json.loads(testset_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Retrieval testset must be a JSON array.")
    return cases


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_case(
    case: dict[str, Any],
    embedder: SentenceTransformerEmbedder,
    vector_store: ChromaVectorStore,
    query_rewriter: QueryRewriter,
) -> dict[str, Any]:
    query = str(case["query"])
    rewritten_query = query_rewriter.rewrite(query)

    started_at = perf_counter()
    embedding_started_at = perf_counter()
    query_embedding = embedder.embed(rewritten_query)
    embedding_ms = (perf_counter() - embedding_started_at) * 1000

    vector_started_at = perf_counter()
    matches = vector_store.query(query_embedding, top_k=TOP_K)
    vector_ms = (perf_counter() - vector_started_at) * 1000
    total_ms = (perf_counter() - started_at) * 1000

    retrieved_titles = [str(match.metadata.get("title", "")) for match in matches]
    expected_titles = {str(title) for title in case.get("expected_titles", [])}
    item_reciprocal_rank = reciprocal_rank(expected_titles, retrieved_titles)

    return {
        "id": case["id"],
        "category": case["category"],
        "query": query,
        "rewritten_query": rewritten_query,
        "expected_titles": sorted(expected_titles),
        "source_doc": case.get("source_doc", ""),
        "retrieved": [
            {
                "rank": rank,
                "id": match.id,
                "title": str(match.metadata.get("title", "")),
                "source": str(match.metadata.get("source", "")),
                "score": match.score,
            }
            for rank, match in enumerate(matches, start=1)
        ],
        "hit_at_1": hit_at_k(expected_titles, retrieved_titles, 1),
        "hit_at_5": hit_at_k(expected_titles, retrieved_titles, TOP_K),
        "reciprocal_rank": item_reciprocal_rank,
        "latency_ms": {
            "embedding": embedding_ms,
            "vector_query": vector_ms,
            "total": total_ms,
        },
    }


def summarize_category(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": len(results),
        "recall_at_1": _mean([item["hit_at_1"] for item in results]),
        "recall_at_5": _mean([item["hit_at_5"] for item in results]),
        "mrr": mean_reciprocal_rank([item["reciprocal_rank"] for item in results]),
    }


def build_report(settings: Settings, cases: list[dict[str, Any]]) -> dict[str, Any]:
    vector_store = ChromaVectorStore(
        persist_dir=settings.chroma_persist_root,
        collection_name=settings.rag_collection_name,
    )
    record_count = vector_store.count()
    if record_count == 0:
        raise RuntimeError(f"Chroma collection '{settings.rag_collection_name}' is empty or missing.")

    embedder = SentenceTransformerEmbedder(
        model_name=settings.embedding_model_name,
        cache_dir=settings.model_cache_root,
        local_files_only=True,
    )
    query_rewriter = QueryRewriter()

    # Warm up model initialization so the latency report reflects per-query retrieval cost.
    embedder.embed("灵山胜境")

    results = [evaluate_case(case, embedder, vector_store, query_rewriter) for case in cases]
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        categories[result["category"]].append(result)

    recall_at_1 = _mean([item["hit_at_1"] for item in results])
    recall_at_5 = _mean([item["hit_at_5"] for item in results])
    mrr = mean_reciprocal_rank([item["reciprocal_rank"] for item in results])
    embedding_latency = summarize_latency([item["latency_ms"]["embedding"] for item in results])
    vector_latency = summarize_latency([item["latency_ms"]["vector_query"] for item in results])
    total_latency = summarize_latency([item["latency_ms"]["total"] for item in results])

    threshold_checks = {
        "recall_at_5": recall_at_5 >= THRESHOLDS["recall_at_5"],
        "mrr": mrr >= THRESHOLDS["mrr"],
        "vector_p95_ms": vector_latency["p95_ms"] < THRESHOLDS["vector_p95_ms"],
    }

    return {
        "mode": "real_chroma_retrieval_v0",
        "scope": "query_rewrite -> embedding -> Chroma Top-5; excludes FAQ, reranker, and LLM",
        "testset": "eval/testset/retrieval_test.json",
        "case_count": len(results),
        "index": {
            "collection": settings.rag_collection_name,
            "record_count": record_count,
            "embedding_model": settings.embedding_model_name,
            "persist_dir": str(settings.chroma_persist_root),
        },
        "metrics": {
            "recall_at_1": recall_at_1,
            "recall_at_5": recall_at_5,
            "mrr": mrr,
        },
        "latency_ms": {
            "embedding": embedding_latency,
            "vector_query": vector_latency,
            "total": total_latency,
        },
        "thresholds": THRESHOLDS,
        "threshold_checks": threshold_checks,
        "passed": all(threshold_checks.values()),
        "by_category": {
            category: summarize_category(category_results)
            for category, category_results in sorted(categories.items())
        },
        "failures": [result for result in results if not result["hit_at_5"]],
        "results": results,
    }


def run() -> Path:
    eval_root = Path(__file__).resolve().parents[1]
    testset_path = eval_root / "testset" / "retrieval_test.json"
    report_path = eval_root / "reports" / "retrieval_v0.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(Settings(), load_cases(testset_path))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "passed": report["passed"],
        "case_count": report["case_count"],
        "metrics": report["metrics"],
        "vector_p95_ms": report["latency_ms"]["vector_query"]["p95_ms"],
        "failure_count": len(report["failures"]),
        "report_path": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report_path


if __name__ == "__main__":
    run()
