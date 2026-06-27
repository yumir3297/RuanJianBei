from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.metrics.accuracy import evaluate_cases  # noqa: E402
from eval.metrics.latency import summarize_latency  # noqa: E402


def load_testset(root: Path, name: str) -> list[dict]:
    return json.loads((root / "testset" / f"{name}.json").read_text(encoding="utf-8"))


def expected_answer_fn(case_by_query: dict[str, dict]):
    def answer(query: str) -> str:
        case = case_by_query[query]
        return str(case.get("expected_answer", ""))

    return answer


def evaluate_dataset(root: Path, name: str) -> dict:
    cases = load_testset(root, name)
    case_by_query = {case["query"]: case for case in cases}
    answer = expected_answer_fn(case_by_query)

    started_at = perf_counter()
    report = evaluate_cases(cases, answer)
    elapsed_ms = int((perf_counter() - started_at) * 1000)

    return {
        "name": name,
        "case_count": len(cases),
        "accuracy": report.to_dict(),
        "latency": summarize_latency([elapsed_ms]),
        "mode": "expected_answer_smoke",
    }


def run(root: Path) -> dict:
    datasets = [evaluate_dataset(root, name) for name in ("faq_test", "knowledge_test", "recommend_test")]
    total_cases = sum(item["case_count"] for item in datasets)
    total_passed = sum(item["accuracy"]["passed"] for item in datasets)

    return {
        "mode": "offline_smoke",
        "description": "Uses expected_answer as answer_fn. Replace answer_fn with backend pipeline/API for real regression.",
        "total_cases": total_cases,
        "total_passed": total_passed,
        "overall_accuracy": total_passed / total_cases if total_cases else 0.0,
        "datasets": datasets,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(run(root), ensure_ascii=False, indent=2))
