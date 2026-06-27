from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402
from app.services.qa.faq_matcher import FAQMatcher  # noqa: E402
from app.services.rag.embedder import SentenceTransformerEmbedder  # noqa: E402
from eval.metrics.latency import summarize_latency  # noqa: E402

THRESHOLDS = [round(value / 100, 2) for value in range(60, 96)]


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array: {path}")
    return data


def build_matcher(settings: Settings) -> tuple[FAQMatcher, float]:
    matcher = FAQMatcher()
    matcher.load_from_file(settings.faq_file)
    embedder = SentenceTransformerEmbedder(
        settings.embedding_model_name,
        cache_dir=settings.model_cache_root,
        local_files_only=True,
    )
    build_ms = matcher.ensure_semantic_index(embedder, threshold=0.0)
    return matcher, build_ms


def evaluate(settings: Settings, cases: list[dict[str, Any]]) -> dict[str, Any]:
    matcher, build_ms = build_matcher(settings)
    if matcher.semantic_index is None:
        raise RuntimeError("FAQ semantic index was not built.")

    raw_results: list[dict[str, Any]] = []
    query_times: list[float] = []
    for case in cases:
        started_at = perf_counter()
        query = str(case["query"])
        decision = matcher.semantic_gate.decide(query)
        match = None
        if decision.allowed:
            match = matcher.semantic_index.match(
                query,
                threshold=-1.0,
                allowed_entry_ids=decision.allowed_entry_ids,
            )
        query_ms = (perf_counter() - started_at) * 1000
        query_times.append(query_ms)
        raw_results.append(
            {
                **case,
                "best_faq_id": match.entry.id if match else None,
                "best_alias": match.alias if match else None,
                "score": match.score if match else 0.0,
                "gate_reason": decision.reason,
                "gate_entity": decision.entity,
                "gate_intent": decision.intent,
                "candidate_entry_count": len(decision.allowed_entry_ids),
                "query_ms": query_ms,
            }
        )

    threshold_results = []
    positives = [item for item in raw_results if item["kind"] == "positive"]
    negatives = [item for item in raw_results if item["kind"] == "negative"]
    for threshold in THRESHOLDS:
        positive_correct = sum(
            item["score"] >= threshold and item["best_faq_id"] == item["expected_faq_id"]
            for item in positives
        )
        positive_wrong = sum(
            item["score"] >= threshold and item["best_faq_id"] != item["expected_faq_id"]
            for item in positives
        )
        negative_false_hits = sum(item["score"] >= threshold for item in negatives)
        threshold_results.append(
            {
                "threshold": threshold,
                "positive_accuracy": positive_correct / len(positives),
                "positive_wrong_rate": positive_wrong / len(positives),
                "negative_rejection_rate": 1 - negative_false_hits / len(negatives),
                "positive_correct": positive_correct,
                "positive_wrong": positive_wrong,
                "negative_false_hits": negative_false_hits,
            }
        )

    passing = [
        item
        for item in threshold_results
        if item["positive_accuracy"] >= 0.8 and item["negative_false_hits"] == 0
    ]
    recommended = min(
        passing,
        key=lambda item: (-item["positive_accuracy"], item["threshold"]),
    ) if passing else None

    return {
        "mode": "faq_semantic_entity_intent_gate_v2",
        "testset": "eval/testset/faq_semantic_test.json",
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "index": {
            "entry_count": len(matcher.entries),
            "alias_count": matcher.semantic_index.alias_count,
            "embedding_model": matcher.semantic_index.model_name,
            "build_ms": build_ms,
        },
        "query_latency_ms": summarize_latency(query_times),
        "recommended": recommended,
        "threshold_results": threshold_results,
        "raw_results": raw_results,
    }


def run() -> Path:
    eval_root = Path(__file__).resolve().parents[1]
    report_path = eval_root / "reports" / "faq_semantic_v2.json"
    report = evaluate(
        Settings(),
        load_json(eval_root / "testset" / "faq_semantic_test.json"),
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "recommended": report["recommended"],
        "index": report["index"],
        "query_latency_ms": report["query_latency_ms"],
        "report_path": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report_path


if __name__ == "__main__":
    run()
