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

TOP_K = 5
MAX_CANDIDATE_K = 20
MATRIX = {
    128: (5,),
    256: (5, 8, 10),
    512: (5, 8, 10),
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Retrieval testset must be a JSON array.")
    return cases


def to_documents(matches: list[VectorSearchResult]) -> list[RetrievedDocument]:
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


def rank(expected_titles: set[str], titles: list[str]) -> int | None:
    for index, title in enumerate(titles, start=1):
        if title in expected_titles:
            return index
    return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def preload_candidates(
    settings: Settings,
    cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    embedder = SentenceTransformerEmbedder(
        settings.embedding_model_name,
        cache_dir=settings.model_cache_root,
        local_files_only=True,
    )
    vector_store = ChromaVectorStore(settings.chroma_persist_root, settings.rag_collection_name)
    query_rewriter = QueryRewriter()
    embedder.embed("灵山胜境")

    prepared: list[dict[str, Any]] = []
    embedding_times: list[float] = []
    vector_times: list[float] = []
    for case in cases:
        query = str(case["query"])
        rewritten = query_rewriter.rewrite(query)

        started_at = perf_counter()
        embedding = embedder.embed(rewritten)
        embedding_times.append((perf_counter() - started_at) * 1000)

        started_at = perf_counter()
        candidates = vector_store.query(embedding, top_k=MAX_CANDIDATE_K)
        vector_times.append((perf_counter() - started_at) * 1000)
        prepared.append(
            {
                "case": case,
                "query": query,
                "rewritten_query": rewritten,
                "candidates": candidates,
            }
        )

    return prepared, {
        "embedding": summarize_latency(embedding_times),
        "vector_query": summarize_latency(vector_times),
        "record_count": vector_store.count(),
    }


def evaluate_configuration(
    prepared: list[dict[str, Any]],
    reranker: CrossEncoderReranker,
    *,
    candidate_k: int,
    max_length: int,
) -> dict[str, Any]:
    warmup_documents = [
        RetrievedDocument(title=f"预热文档 {index}", content="灵山胜境佛教文化景区资料。")
        for index in range(candidate_k)
    ]
    reranker.rerank("灵山胜境", warmup_documents, top_k=TOP_K)

    results: list[dict[str, Any]] = []
    reranker_times: list[float] = []
    for item in prepared:
        case = item["case"]
        expected_titles = {str(title) for title in case.get("expected_titles", [])}
        candidates = item["candidates"][:candidate_k]

        started_at = perf_counter()
        reranked = reranker.rerank(item["query"], to_documents(candidates), top_k=TOP_K)
        reranker_ms = (perf_counter() - started_at) * 1000
        reranker_times.append(reranker_ms)

        raw_titles = [str(match.metadata.get("title", "")) for match in candidates[:TOP_K]]
        reranked_titles = [result.document.title for result in reranked]
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected_titles": sorted(expected_titles),
                "raw_rank": rank(expected_titles, raw_titles),
                "reranked_rank": rank(expected_titles, reranked_titles),
                "raw_top_1": raw_titles[0] if raw_titles else None,
                "reranked_top_1": reranked_titles[0] if reranked_titles else None,
                "reranker_ms": reranker_ms,
            }
        )

    hit_at_1 = [hit_at_k(set(item["expected_titles"]), [item["reranked_top_1"]], 1) for item in results]
    hit_at_5 = [
        1.0 if item["reranked_rank"] is not None and item["reranked_rank"] <= TOP_K else 0.0
        for item in results
    ]
    reciprocal_ranks = [
        0.0 if item["reranked_rank"] is None else 1.0 / item["reranked_rank"]
        for item in results
    ]
    improved = [item["id"] for item in results if (item["raw_rank"] or 999) > (item["reranked_rank"] or 999)]
    degraded = [item["id"] for item in results if (item["reranked_rank"] or 999) > (item["raw_rank"] or 999)]

    metrics = {
        "recall_at_1": mean(hit_at_1),
        "recall_at_5": mean(hit_at_5),
        "mrr": mean_reciprocal_rank(reciprocal_ranks),
    }
    accuracy_passed = all(metrics[key] >= 1.0 for key in ("recall_at_1", "recall_at_5", "mrr"))
    return {
        "candidate_k": candidate_k,
        "top_k": TOP_K,
        "max_length": max_length,
        "metrics": metrics,
        "latency_ms": summarize_latency(reranker_times),
        "accuracy_passed": accuracy_passed,
        "improved_ids": improved,
        "degraded_ids": degraded,
        "results": results,
    }


def score_gate_analysis(prepared: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in prepared:
        case = item["case"]
        expected_titles = {str(title) for title in case.get("expected_titles", [])}
        candidates = item["candidates"]
        titles = [str(match.metadata.get("title", "")) for match in candidates]
        top_score = candidates[0].score if candidates else 0.0
        second_score = candidates[1].score if len(candidates) > 1 else 0.0
        rows.append(
            {
                "id": case["id"],
                "raw_hit_at_1": hit_at_k(expected_titles, titles, 1),
                "top_1_score": top_score,
                "top_1_top_2_margin": top_score - second_score,
            }
        )

    wrong = [item for item in rows if not item["raw_hit_at_1"]]
    correct = [item for item in rows if item["raw_hit_at_1"]]
    return {
        "conclusion": "No global score or margin threshold is enabled by this 30-case dataset.",
        "wrong_top_1": wrong,
        "correct_score_range": {
            "min": min(item["top_1_score"] for item in correct),
            "max": max(item["top_1_score"] for item in correct),
        },
        "correct_margin_range": {
            "min": min(item["top_1_top_2_margin"] for item in correct),
            "max": max(item["top_1_top_2_margin"] for item in correct),
        },
    }


def build_report(settings: Settings, cases: list[dict[str, Any]]) -> dict[str, Any]:
    prepared, retrieval_stats = preload_candidates(settings, cases)
    configurations: list[dict[str, Any]] = []
    by_length: dict[int, list[int]] = defaultdict(list)
    for max_length, candidate_sizes in MATRIX.items():
        by_length[max_length].extend(candidate_sizes)

    for max_length, candidate_sizes in sorted(by_length.items()):
        reranker = CrossEncoderReranker(
            settings.reranker_model_name,
            cache_dir=settings.model_cache_root,
            batch_size=settings.reranker_batch_size,
            max_length=max_length,
            local_files_only=True,
        )
        for candidate_k in candidate_sizes:
            configurations.append(
                evaluate_configuration(
                    prepared,
                    reranker,
                    candidate_k=candidate_k,
                    max_length=max_length,
                )
            )

    passing = [item for item in configurations if item["accuracy_passed"]]
    recommended = min(passing, key=lambda item: item["latency_ms"]["p95_ms"]) if passing else None
    return {
        "mode": "reranker_performance_gate_v1",
        "testset": "eval/testset/retrieval_test.json",
        "case_count": len(cases),
        "fixed": {
            "model": settings.reranker_model_name,
            "batch_size": settings.reranker_batch_size,
            "top_k": TOP_K,
            "device": "cpu",
        },
        "retrieval_baseline": retrieval_stats,
        "score_gate_analysis": score_gate_analysis(prepared),
        "configurations": configurations,
        "recommended": None
        if recommended is None
        else {
            "candidate_k": recommended["candidate_k"],
            "max_length": recommended["max_length"],
            "metrics": recommended["metrics"],
            "latency_ms": recommended["latency_ms"],
        },
    }


def run() -> Path:
    eval_root = Path(__file__).resolve().parents[1]
    testset_path = eval_root / "testset" / "retrieval_test.json"
    report_path = eval_root / "reports" / "reranker_gate_v1.json"
    report = build_report(Settings(), load_cases(testset_path))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "case_count": report["case_count"],
        "recommended": report["recommended"],
        "configurations": [
            {
                "candidate_k": item["candidate_k"],
                "max_length": item["max_length"],
                "metrics": item["metrics"],
                "p50_ms": item["latency_ms"]["p50_ms"],
                "p95_ms": item["latency_ms"]["p95_ms"],
                "accuracy_passed": item["accuracy_passed"],
            }
            for item in report["configurations"]
        ],
        "report_path": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report_path


if __name__ == "__main__":
    run()
