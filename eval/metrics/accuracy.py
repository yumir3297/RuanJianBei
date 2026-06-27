from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path


def contains_required_points(answer: str, must_contain: list[str]) -> bool:
    return all(token in answer for token in must_contain)


def excludes_forbidden_points(answer: str, must_not_contain: list[str]) -> bool:
    return all(token not in answer for token in must_not_contain)


@dataclass(slots=True)
class AccuracyFailure:
    id: str
    query: str
    expected_contains: list[str]
    expected_excludes: list[str]
    actual_answer: str
    reason: str


@dataclass(slots=True)
class AccuracyReport:
    total: int
    passed: int
    accuracy: float
    failures: list[AccuracyFailure]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "accuracy": self.accuracy,
            "failures": [asdict(item) for item in self.failures],
        }


def evaluate_cases(cases: list[dict], answer_fn: Callable[[str], str]) -> AccuracyReport:
    passed = 0
    failures: list[AccuracyFailure] = []

    for case in cases:
        answer = answer_fn(case["query"])
        must_contain = list(case.get("must_contain") or case.get("key_points") or [])
        must_not_contain = list(case.get("must_not_contain") or [])

        contains_required = contains_required_points(answer, must_contain)
        excludes_forbidden = excludes_forbidden_points(answer, must_not_contain)

        if contains_required and excludes_forbidden:
            passed += 1
            continue

        reasons = []
        if not contains_required:
            reasons.append("missing_required_token")
        if not excludes_forbidden:
            reasons.append("contains_forbidden_token")

        failures.append(
            AccuracyFailure(
                id=str(case.get("id", "")),
                query=str(case.get("query", "")),
                expected_contains=must_contain,
                expected_excludes=must_not_contain,
                actual_answer=answer[:200],
                reason=",".join(reasons),
            )
        )

    total = len(cases)
    return AccuracyReport(
        total=total,
        passed=passed,
        accuracy=passed / total if total else 0.0,
        failures=failures,
    )


def evaluate(testset_path: Path, answer_fn: Callable[[str], str]) -> dict:
    cases = json.loads(testset_path.read_text(encoding="utf-8"))
    return evaluate_cases(cases, answer_fn).to_dict()
