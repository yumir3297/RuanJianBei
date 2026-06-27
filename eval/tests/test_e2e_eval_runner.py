from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from eval.scripts.e2e_eval_core import (
    E2ECase,
    build_execution_report,
    evaluate_remote_cases,
    load_cases,
    validate_cases,
)
from eval.scripts.build_e2e_qa_100 import EXPECTED_DISTRIBUTION


def sse(*events: tuple[str, dict]) -> str:
    return "".join(
        f"event: {event_type}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        for event_type, payload in events
    )


def response_for(query: str) -> str:
    if "只有最终文本" in query:
        return sse(
            ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
            ("text", {"text": "灵山大佛高88米。[证据1]", "is_complete": True}),
            ("done", {}),
        )
    if "缺少引用" in query:
        return sse(
            ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
            ("text_chunk", {"token": "灵山大佛高88米"}),
            ("text", {"text": "灵山大佛高88米。", "is_complete": True}),
            ("done", {}),
        )
    if "天气" in query:
        return sse(
            ("text_chunk", {"token": "根据现有景区资料，暂时无法确定实时天气。"}),
            ("text", {"text": "根据现有景区资料，暂时无法确定实时天气。", "is_complete": True}),
            ("done", {}),
        )
    if "禁用事实" in query:
        return sse(
            ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
            ("text_chunk", {"token": "灵山大佛高88米，免费入园。[证据1]"}),
            ("text", {"text": "灵山大佛高88米，免费入园。[证据1]", "is_complete": True}),
            ("done", {}),
        )
    return sse(
        ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
        ("text_chunk", {"token": "灵山大佛高88米"}),
        ("text", {"text": "灵山大佛高88米。[证据1]", "is_complete": True}),
        ("done", {}),
    )


def mock_cases() -> list[E2ECase]:
    return [
        E2ECase(
            id="PASS",
            category="fact_qa",
            query="灵山大佛有多高？",
            expected_behavior="answer_with_evidence",
            expected_sources=["灵山大佛"],
            required_facts=["88米"],
        ),
        E2ECase(
            id="NO_CITATION",
            category="fact_qa",
            query="缺少引用：灵山大佛有多高？",
            expected_behavior="answer_with_evidence",
            expected_sources=["灵山大佛"],
            required_facts=["88米"],
        ),
        E2ECase(
            id="REFUSAL",
            category="blind_spot_refusal",
            query="明天天气怎么样？",
            expected_behavior="refuse_without_evidence",
            forbidden_facts=["一定下雨"],
        ),
        E2ECase(
            id="FORBIDDEN",
            category="fact_qa",
            query="禁用事实：灵山大佛有多高？",
            expected_behavior="answer_with_evidence",
            expected_sources=["灵山大佛"],
            required_facts=["88米"],
            forbidden_facts=["免费入园"],
        ),
        E2ECase(
            id="TEXT_ONLY",
            category="fact_qa",
            query="只有最终文本：灵山大佛有多高？",
            expected_behavior="answer_with_evidence",
            expected_sources=["灵山大佛"],
            required_facts=["88米"],
        ),
    ]


def test_seed_testset_is_valid() -> None:
    cases = load_cases(Path(__file__).resolve().parents[1] / "testset" / "e2e_qa_seed.json")

    assert len(cases) == 10
    assert validate_cases(cases) == []


def test_full_100_testset_is_valid_and_balanced() -> None:
    cases = load_cases(Path(__file__).resolve().parents[1] / "testset" / "e2e_qa_100.json")
    distribution = {}
    for case in cases:
        distribution[case.category] = distribution.get(case.category, 0) + 1

    assert len(cases) == 100
    assert distribution == EXPECTED_DISTRIBUTION
    assert validate_cases(cases) == []


def test_mock_backend_covers_scoring_paths_and_warm_latency() -> None:
    async def run():
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                text=response_for(payload["query"]),
                headers={"Content-Type": "text/event-stream"},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await evaluate_remote_cases(
                mock_cases(),
                endpoint="http://mock.local/api/chat/stream",
                client=client,
            )

    results = asyncio.run(run())
    by_id = {item["id"]: item for item in results}

    assert by_id["PASS"]["accuracy_pass"] is True
    assert by_id["NO_CITATION"]["accuracy_pass"] is False
    assert by_id["NO_CITATION"]["failure_reasons"] == ["citation_present"]
    assert by_id["REFUSAL"]["accuracy_pass"] is True
    assert by_id["FORBIDDEN"]["accuracy_pass"] is False
    assert by_id["FORBIDDEN"]["failure_reasons"] == ["forbidden_fact_absent"]
    assert by_id["TEXT_ONLY"]["accuracy_pass"] is True
    assert by_id["TEXT_ONLY"]["first_text_ms"] is not None
    assert by_id["PASS"]["is_cold_start"] is True
    assert by_id["NO_CITATION"]["is_cold_start"] is False

    report = build_execution_report(
        mode="local-server",
        testset_path=Path("mock.json"),
        cases=mock_cases(),
        results=results,
    )

    assert report["metrics"]["accuracy"] == 0.6
    assert report["latency_ms"]["total_all"]["count"] == 5
    assert report["latency_ms"]["total_warm"]["count"] == 4
