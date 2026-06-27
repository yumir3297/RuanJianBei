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
from app.services.rag.base import RetrievedDocument  # noqa: E402
from app.services.rag.cross_encoder_reranker import CrossEncoderReranker  # noqa: E402
from app.services.rag.embedder import SentenceTransformerEmbedder  # noqa: E402
from app.services.rag.query_rewriter import QueryRewriter  # noqa: E402
from app.services.rag.vector_store import ChromaVectorStore, VectorSearchResult  # noqa: E402
from eval.metrics.latency import summarize_latency  # noqa: E402
from eval.metrics.retrieval import hit_at_k, mean_reciprocal_rank, reciprocal_rank  # noqa: E402

CANDIDATE_K = 20
TOP_K = 5
THRESHOLDS = {
    "reranked_recall_at_5": 0.90,
    "reranked_recall_at_5_not_lower_than_raw": True,
    "reranked_mrr_not_lower_than_raw": True,
    "reranker_p95_ms": 150.0,
}


def load_cases(testset_path: Path) -> list[dict[str, Any]]:
    cases = json.loads(testset_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Retrieval testset must be a JSON array.")
    return cases


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _titles(matches: list[VectorSearchResult]) -> list[str]:
    return [str(match.metadata.get("title", "")) for match in matches]


def _rank(expected_titles: set[str], retrieved_titles: list[str]) -> int | None:
    for rank, title in enumerate(retrieved_titles, start=1):
        if title in expected_titles:
            return rank
    return None


def _serialize_vector_matches(matches: list[VectorSearchResult]) -> list[dict[str, Any]]:
    return [
        {
            "rank": rank,
            "id": match.id,
            "title": str(match.metadata.get("title", "")),
            "source": str(match.metadata.get("source", "")),
            "score": match.score,
        }
        for rank, match in enumerate(matches, start=1)
    ]


def _to_documents(matches: list[VectorSearchResult]) -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            title=str(match.metadata.get("title", "")),
            content=match.document,
            snippet=match.document[:200],
            source=str(match.metadata.get("source", "")),
            score=match.score,
        )
        for match in matches
    ]


def _metrics(expected_titles: set[str], retrieved_titles: list[str]) -> dict[str, float]:
    return {
        "hit_at_1": hit_at_k(expected_titles, retrieved_titles, 1),
        "hit_at_5": hit_at_k(expected_titles, retrieved_titles, TOP_K),
        "reciprocal_rank": reciprocal_rank(expected_titles, retrieved_titles),
    }


def evaluate_case(
    case: dict[str, Any],
    embedder: SentenceTransformerEmbedder,
    vector_store: ChromaVectorStore,
    query_rewriter: QueryRewriter,
    reranker: CrossEncoderReranker,
) -> dict[str, Any]:
    query = str(case["query"])
    rewritten_query = query_rewriter.rewrite(query)
    expected_titles = {str(title) for title in case.get("expected_titles", [])}

    started_at = perf_counter()
    embedding_started_at = perf_counter()
    query_embedding = embedder.embed(rewritten_query)
    embedding_ms = (perf_counter() - embedding_started_at) * 1000

    vector_started_at = perf_counter()
    candidates = vector_store.query(query_embedding, top_k=CANDIDATE_K)
    vector_ms = (perf_counter() - vector_started_at) * 1000

    raw_top_five = candidates[:TOP_K]
    raw_titles = _titles(raw_top_five)
    candidate_titles = _titles(candidates)

    rerank_started_at = perf_counter()
    reranked_results = reranker.rerank(query, _to_documents(candidates), top_k=TOP_K)
    rerank_ms = (perf_counter() - rerank_started_at) * 1000
    total_ms = (perf_counter() - started_at) * 1000

    reranked_titles = [item.document.title for item in reranked_results]
    raw_rank = _rank(expected_titles, candidate_titles)
    reranked_rank = _rank(expected_titles, reranked_titles)
    rank_change = None
    if raw_rank is not None and reranked_rank is not None:
        rank_change = raw_rank - reranked_rank

    return {
        "id": case["id"],
        "category": case["category"],
        "query": query,
        "rewritten_query": rewritten_query,
        "expected_titles": sorted(expected_titles),
        "source_doc": case.get("source_doc", ""),
        "raw": {
            "metrics": _metrics(expected_titles, raw_titles),
            "expected_rank_in_top_20": raw_rank,
            "retrieved": _serialize_vector_matches(raw_top_five),
        },
        "reranked": {
            "metrics": _metrics(expected_titles, reranked_titles),
            "expected_rank_in_top_5": reranked_rank,
            "rank_change": rank_change,
            "retrieved": [
                {
                    "rank": rank,
                    "title": item.document.title,
                    "source": item.document.source,
                    "score": item.score,
                }
                for rank, item in enumerate(reranked_results, start=1)
            ],
        },
        "latency_ms": {
            "embedding": embedding_ms,
            "vector_query": vector_ms,
            "reranker": rerank_ms,
            "total": total_ms,
        },
    }


def summarize_metrics(results: list[dict[str, Any]], stage: str) -> dict[str, float]:
    metrics = [item[stage]["metrics"] for item in results]
    return {
        "recall_at_1": _mean([item["hit_at_1"] for item in metrics]),
        "recall_at_5": _mean([item["hit_at_5"] for item in metrics]),
        "mrr": mean_reciprocal_rank([item["reciprocal_rank"] for item in metrics]),
    }


def summarize_category(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": len(results),
        "raw": summarize_metrics(results, "raw"),
        "reranked": summarize_metrics(results, "reranked"),
    }


def build_report(settings: Settings, cases: list[dict[str, Any]]) -> dict[str, Any]:
    vector_store = ChromaVectorStore(
        persist_dir=settings.chroma_persist_root,
        collection_name=settings.rag_collection_name,
    )
    record_count = vector_store.count()
    if record_count == 0:
        raise RuntimeError(f"Chroma collection '{settings.rag_collection_name}' is empty or missing.")

    embedder_started_at = perf_counter()
    embedder = SentenceTransformerEmbedder(
        model_name=settings.embedding_model_name,
        cache_dir=settings.model_cache_root,
        local_files_only=True,
    )
    embedder_load_ms = (perf_counter() - embedder_started_at) * 1000

    reranker_started_at = perf_counter()
    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model_name,
        cache_dir=settings.model_cache_root,
        batch_size=settings.reranker_batch_size,
        max_length=settings.reranker_max_length,
        local_files_only=True,
    )
    reranker_load_ms = (perf_counter() - reranker_started_at) * 1000
    query_rewriter = QueryRewriter()

    embedder.embed("灵山胜境")
    warmup_documents = [
        RetrievedDocument(title=f"预热文档 {index}", content="灵山胜境佛教文化景区资料。")
        for index in range(CANDIDATE_K)
    ]
    warmup_started_at = perf_counter()
    reranker.rerank("灵山胜境", warmup_documents, top_k=TOP_K)
    reranker_warmup_ms = (perf_counter() - warmup_started_at) * 1000

    results = [
        evaluate_case(case, embedder, vector_store, query_rewriter, reranker)
        for case in cases
    ]
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        categories[result["category"]].append(result)

    raw_metrics = summarize_metrics(results, "raw")
    reranked_metrics = summarize_metrics(results, "reranked")
    latency = {
        stage: summarize_latency([item["latency_ms"][stage] for item in results])
        for stage in ("embedding", "vector_query", "reranker", "total")
    }
    threshold_checks = {
        "reranked_recall_at_5": reranked_metrics["recall_at_5"] >= THRESHOLDS["reranked_recall_at_5"],
        "reranked_recall_at_5_not_lower_than_raw": (
            reranked_metrics["recall_at_5"] >= raw_metrics["recall_at_5"]
        ),
        "reranked_mrr_not_lower_than_raw": reranked_metrics["mrr"] >= raw_metrics["mrr"],
        "reranker_p95_ms": latency["reranker"]["p95_ms"] < THRESHOLDS["reranker_p95_ms"],
    }

    improved = [item for item in results if (item["reranked"]["rank_change"] or 0) > 0]
    degraded = [
        item
        for item in results
        if item["reranked"]["rank_change"] is None or item["reranked"]["rank_change"] < 0
    ]

    return {
        "mode": "real_cross_encoder_reranker_v0",
        "scope": "query rewrite -> embedding -> Chroma Top-20 -> CrossEncoder Top-5; excludes FAQ and LLM",
        "testset": "eval/testset/retrieval_test.json",
        "case_count": len(results),
        "index": {
            "collection": settings.rag_collection_name,
            "record_count": record_count,
            "embedding_model": settings.embedding_model_name,
            "reranker_model": settings.reranker_model_name,
            "candidate_k": CANDIDATE_K,
            "top_k": TOP_K,
            "reranker_batch_size": settings.reranker_batch_size,
            "reranker_max_length": settings.reranker_max_length,
            "persist_dir": str(settings.chroma_persist_root),
            "model_cache_dir": str(settings.model_cache_root),
        },
        "initialization_ms": {
            "embedder_load": embedder_load_ms,
            "reranker_load": reranker_load_ms,
            "reranker_top_20_warmup": reranker_warmup_ms,
        },
        "metrics": {
            "raw": raw_metrics,
            "reranked": reranked_metrics,
            "delta": {
                key: reranked_metrics[key] - raw_metrics[key]
                for key in ("recall_at_1", "recall_at_5", "mrr")
            },
        },
        "latency_ms": latency,
        "thresholds": THRESHOLDS,
        "threshold_checks": threshold_checks,
        "accuracy_passed": all(
            threshold_checks[key]
            for key in (
                "reranked_recall_at_5",
                "reranked_recall_at_5_not_lower_than_raw",
                "reranked_mrr_not_lower_than_raw",
            )
        ),
        "performance_passed": threshold_checks["reranker_p95_ms"],
        "passed": all(threshold_checks.values()),
        "by_category": {
            category: summarize_category(category_results)
            for category, category_results in sorted(categories.items())
        },
        "movement_summary": {
            "improved_count": len(improved),
            "degraded_or_missing_count": len(degraded),
            "improved_ids": [item["id"] for item in improved],
            "degraded_or_missing_ids": [item["id"] for item in degraded],
        },
        "raw_top_5_failures": [item for item in results if not item["raw"]["metrics"]["hit_at_5"]],
        "reranked_top_5_failures": [
            item for item in results if not item["reranked"]["metrics"]["hit_at_5"]
        ],
        "results": results,
    }


def run() -> Path:
    eval_root = Path(__file__).resolve().parents[1]
    testset_path = eval_root / "testset" / "retrieval_test.json"
    report_path = eval_root / "reports" / "reranker_v0.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(Settings(), load_cases(testset_path))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "passed": report["passed"],
        "accuracy_passed": report["accuracy_passed"],
        "performance_passed": report["performance_passed"],
        "case_count": report["case_count"],
        "metrics": report["metrics"],
        "reranker_p50_ms": report["latency_ms"]["reranker"]["p50_ms"],
        "reranker_p95_ms": report["latency_ms"]["reranker"]["p95_ms"],
        "reranked_failure_count": len(report["reranked_top_5_failures"]),
        "report_path": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report_path


if __name__ == "__main__":
    run()
