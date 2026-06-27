from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

import httpx

from eval.metrics.latency import summarize_latency


CATEGORIES = {
    "fact_qa",
    "history_culture",
    "attraction_detail",
    "route_planning",
    "practical_info",
    "guided_selection",
    "followup_context",
    "blind_spot_refusal",
}

EXPECTED_BEHAVIOR_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "answer_with_evidence": {
        "must_pass": (
            "stream_completed",
            "source_hit",
            "required_fact_hit",
            "forbidden_fact_absent",
            "citation_present",
        ),
        "optional": ("refusal_correct",),
    },
    "refuse_without_evidence": {
        "must_pass": (
            "stream_completed",
            "refusal_correct",
            "forbidden_fact_absent",
        ),
        "optional": ("source_hit", "required_fact_hit", "citation_present"),
    },
}

REFUSAL_MARKERS = (
    "无法确定",
    "暂时无法",
    "没有足够",
    "资料不足",
    "不能确定",
    "以景区官方",
    "建议咨询",
    "无法提供实时",
)


@dataclass(slots=True)
class E2ECase:
    id: str
    category: str
    query: str
    expected_behavior: str
    expected_sources: list[str] = field(default_factory=list)
    required_facts: list[str] = field(default_factory=list)
    forbidden_facts: list[str] = field(default_factory=list)
    selection: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    notes: str = ""


@dataclass(slots=True)
class ChatEvalResponse:
    case_id: str
    status_code: int | None
    answer: str
    sources: list[dict[str, Any]]
    event_types: list[str]
    first_text_ms: float | None
    total_ms: float
    is_cold_start: bool
    error_type: str | None = None
    error_message: str | None = None


def load_cases(testset_path: Path) -> list[E2ECase]:
    raw_cases = json.loads(testset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError("E2E testset must be a JSON array.")
    return [case_from_dict(item) for item in raw_cases]


def case_from_dict(item: dict[str, Any]) -> E2ECase:
    return E2ECase(
        id=str(item.get("id", "")).strip(),
        category=str(item.get("category", "")).strip(),
        query=str(item.get("query", "")).strip(),
        expected_behavior=str(item.get("expected_behavior", "")).strip(),
        expected_sources=_string_list(item.get("expected_sources", [])),
        required_facts=_string_list(item.get("required_facts", [])),
        forbidden_facts=_string_list(item.get("forbidden_facts", [])),
        selection=_optional_dict(item.get("selection")),
        context=_optional_dict(item.get("context")),
        notes=str(item.get("notes", "")).strip(),
    )


def validate_cases(cases: list[E2ECase]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, case in enumerate(cases, start=1):
        prefix = f"case[{index}]"
        if not case.id:
            errors.append(f"{prefix}: id is required.")
        elif case.id in seen_ids:
            errors.append(f"{prefix}: duplicate id '{case.id}'.")
        seen_ids.add(case.id)

        if case.category not in CATEGORIES:
            errors.append(f"{prefix} {case.id}: unknown category '{case.category}'.")
        if not case.query:
            errors.append(f"{prefix} {case.id}: query is required.")
        if case.expected_behavior not in EXPECTED_BEHAVIOR_RULES:
            errors.append(
                f"{prefix} {case.id}: unknown expected_behavior '{case.expected_behavior}'."
            )

        if case.expected_behavior == "answer_with_evidence":
            if not case.expected_sources:
                errors.append(f"{prefix} {case.id}: expected_sources is required.")
            if not case.required_facts:
                errors.append(f"{prefix} {case.id}: required_facts is required.")
        elif case.expected_behavior == "refuse_without_evidence":
            if case.required_facts:
                errors.append(
                    f"{prefix} {case.id}: refusal cases should not define required_facts."
                )

    return errors


def build_dry_run_report(testset_path: Path, cases: list[E2ECase]) -> dict[str, Any]:
    errors = validate_cases(cases)
    return {
        "mode": "dry-run",
        "testset": str(testset_path),
        "case_count": len(cases),
        "valid": not errors,
        "errors": errors,
        "category_distribution": dict(Counter(case.category for case in cases)),
        "behavior_distribution": dict(Counter(case.expected_behavior for case in cases)),
        "expected_behavior_rules": EXPECTED_BEHAVIOR_RULES,
        "cases": [asdict(case) for case in cases],
    }


async def iter_sse_events(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, Any]]:
    event_type: str | None = None
    data_lines: list[str] = []
    async for line in lines:
        if not line:
            if event_type and data_lines:
                yield event_type, json.loads("\n".join(data_lines))
            event_type = None
            data_lines = []
            continue
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if event_type and data_lines:
        yield event_type, json.loads("\n".join(data_lines))


async def request_case(
    case: E2ECase,
    *,
    endpoint: str,
    client: httpx.AsyncClient,
    is_cold_start: bool,
) -> ChatEvalResponse:
    started_at = perf_counter()
    status_code: int | None = None
    first_text_ms: float | None = None
    answer = ""
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    event_types: list[str] = []

    payload: dict[str, Any] = {
        "query": case.query,
        "session_id": f"b2-eval-{case.id}",
        "text_only": True,
    }
    if case.selection is not None:
        payload["selection"] = case.selection
    if case.context is not None:
        payload["context"] = case.context

    try:
        async with client.stream("POST", endpoint, json=payload) as response:
            status_code = response.status_code
            response.raise_for_status()
            async for event_type, event_payload in iter_sse_events(response.aiter_lines()):
                event_types.append(event_type)
                if event_type == "sources":
                    docs = event_payload.get("docs", [])
                    if isinstance(docs, list):
                        sources = [item for item in docs if isinstance(item, dict)]
                elif event_type == "text_chunk":
                    if first_text_ms is None:
                        first_text_ms = (perf_counter() - started_at) * 1000
                    token = str(event_payload.get("token") or "")
                    chunks.append(token)
                elif event_type == "text":
                    if first_text_ms is None:
                        first_text_ms = (perf_counter() - started_at) * 1000
                    answer = str(event_payload.get("text") or "")
    except Exception as exc:
        return ChatEvalResponse(
            case_id=case.id,
            status_code=status_code,
            answer=answer or "".join(chunks),
            sources=sources,
            event_types=event_types,
            first_text_ms=first_text_ms,
            total_ms=(perf_counter() - started_at) * 1000,
            is_cold_start=is_cold_start,
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )

    return ChatEvalResponse(
        case_id=case.id,
        status_code=status_code,
        answer=answer or "".join(chunks),
        sources=sources,
        event_types=event_types,
        first_text_ms=first_text_ms,
        total_ms=(perf_counter() - started_at) * 1000,
        is_cold_start=is_cold_start,
    )


async def evaluate_remote_cases(
    cases: list[E2ECase],
    *,
    endpoint: str,
    client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        response = await request_case(
            case,
            endpoint=endpoint,
            client=client,
            is_cold_start=index == 0,
        )
        results.append(score_case(case, response))
        if (index + 1) % 10 == 0 and index + 1 < len(cases):
            await asyncio.sleep(2.0)
    return results


def score_case(case: E2ECase, response: ChatEvalResponse) -> dict[str, Any]:
    checks = build_checks(case, response)
    rules = EXPECTED_BEHAVIOR_RULES[case.expected_behavior]
    failed_required = [name for name in rules["must_pass"] if not checks.get(name, False)]
    return {
        "id": case.id,
        "category": case.category,
        "query": case.query,
        "expected_behavior": case.expected_behavior,
        "status_code": response.status_code,
        "answer": response.answer,
        "sources": response.sources,
        "event_types": response.event_types,
        "first_text_ms": response.first_text_ms,
        "total_ms": response.total_ms,
        "is_cold_start": response.is_cold_start,
        "checks": checks,
        "must_pass": list(rules["must_pass"]),
        "optional": list(rules["optional"]),
        "accuracy_pass": not failed_required and response.error_type is None,
        "failure_reasons": failed_required,
        "error_type": response.error_type,
        "error_message": response.error_message,
    }


def build_checks(case: E2ECase, response: ChatEvalResponse) -> dict[str, bool]:
    answer = response.answer
    source_text = "\n".join(
        " ".join(
            str(source.get(key, ""))
            for key in ("evidence_id", "title", "snippet", "source")
        )
        for source in response.sources
    )
    return {
        "stream_completed": "done" in response.event_types and response.status_code == 200,
        "source_hit": _all_terms_present(source_text, case.expected_sources),
        "required_fact_hit": _all_terms_present(answer, case.required_facts),
        "forbidden_fact_absent": not _any_term_present(answer, case.forbidden_facts),
        "citation_present": "[证据" in answer,
        "refusal_correct": _any_term_present(answer, REFUSAL_MARKERS),
    }


def build_execution_report(
    *,
    mode: str,
    testset_path: Path,
    cases: list[E2ECase],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    answer_cases = [
        result for result in results if result["expected_behavior"] == "answer_with_evidence"
    ]
    refusal_cases = [
        result for result in results if result["expected_behavior"] == "refuse_without_evidence"
    ]
    warm_results = [result for result in results if not result["is_cold_start"]]

    return {
        "mode": mode,
        "testset": str(testset_path),
        "case_count": len(cases),
        "category_distribution": dict(Counter(case.category for case in cases)),
        "behavior_distribution": dict(Counter(case.expected_behavior for case in cases)),
        "expected_behavior_rules": EXPECTED_BEHAVIOR_RULES,
        "metrics": {
            "accuracy": _rate(results, lambda item: item["accuracy_pass"]),
            "evidence_rate": _rate(
                answer_cases,
                lambda item: item["checks"]["citation_present"],
            ),
            "refusal_pass_rate": _rate(
                refusal_cases,
                lambda item: item["checks"]["refusal_correct"] and item["accuracy_pass"],
            ),
            "source_hit_rate": _rate(results, lambda item: item["checks"]["source_hit"]),
        },
        "latency_ms": {
            "first_text_all": summarize_latency(
                [
                    item["first_text_ms"]
                    for item in results
                    if item["first_text_ms"] is not None
                ]
            ),
            "first_text_warm": summarize_latency(
                [
                    item["first_text_ms"]
                    for item in warm_results
                    if item["first_text_ms"] is not None
                ]
            ),
            "total_all": summarize_latency([item["total_ms"] for item in results]),
            "total_warm": summarize_latency([item["total_ms"] for item in warm_results]),
        },
        "failures": [item for item in results if not item["accuracy_pass"]],
        "results": results,
    }


def write_report(report: dict[str, Any], report_path: Path) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return value if isinstance(value, dict) else None


_FORMAT_NORMALIZATIONS = [
    (re.compile(r"(\d+)㎡"), r"\1平方米"),
    (re.compile(r"(\d+)m²"), r"\1平方米"),
    (re.compile(r"(\d+)km(?=\D|$)"), r"\1公里"),
    (re.compile(r"(\d+)m(?=\D|$)"), r"\1米"),
    (re.compile(r"(\d+)kg(?=\D|$)"), r"\1公斤"),
    (re.compile(r"(\d+)t(?=\D|$)"), r"\1吨"),
    (re.compile(r"(\d+)h(?=\D|$)"), r"\1小时"),
    (re.compile(r"(\d+)min(?=\D|$)"), r"\1分钟"),
]


def _normalize_text(text: str) -> str:
    t = text.casefold()
    for pattern, replacement in _FORMAT_NORMALIZATIONS:
        t = pattern.sub(replacement, t)
    return t


def _all_terms_present(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    if not terms:
        return True
    normalized = _normalize_text(text)
    return all(_normalize_text(term) in normalized for term in terms)


def _any_term_present(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(term.casefold() in normalized for term in terms)


def _rate(items: list[dict[str, Any]], predicate) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if predicate(item)) / len(items)


def run_async(coro):
    return asyncio.run(coro)
