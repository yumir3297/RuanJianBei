from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

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
            ("done", {"completion": "complete"}),
        )
    if "缺少引用" in query:
        return sse(
            ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
            ("text_chunk", {"token": "灵山大佛高88米"}),
            ("text", {"text": "灵山大佛高88米。", "is_complete": True}),
            ("done", {"completion": "complete"}),
        )
    if "天气" in query:
        return sse(
            ("text_chunk", {"token": "根据现有景区资料，暂时无法确定实时天气。"}),
            ("text", {"text": "根据现有景区资料，暂时无法确定实时天气。", "is_complete": True}),
            ("done", {"completion": "complete"}),
        )
    if "禁用事实" in query:
        return sse(
            ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
            ("text_chunk", {"token": "灵山大佛高88米，免费入园。[证据1]"}),
            ("text", {"text": "灵山大佛高88米，免费入园。[证据1]", "is_complete": True}),
            ("done", {"completion": "complete"}),
        )
    return sse(
        ("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
        ("text_chunk", {"token": "灵山大佛高88米"}),
        ("text", {"text": "灵山大佛高88米。[证据1]", "is_complete": True}),
        ("done", {"completion": "complete"}),
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
    assert report["metric_notes"]["human_review_required"] is True
    assert "语义" in report["metric_notes"]["evidence_rate"]
    assert report["latency_ms"]["total_all"]["count"] == 5
    assert report["latency_ms"]["total_warm"]["count"] == 4


@pytest.mark.parametrize("terminal", [
    (("done", {"completion": "incomplete"}),),
    (("error", {"message": "服务中断"}), ("done", {"completion": "complete"})),
    (("done", {}),),
])
def test_incomplete_or_error_stream_cannot_pass_even_when_content_matches(terminal):
    async def scenario():
        async def handler(_request):
            body = sse(("sources", {"docs": [{"evidence_id": "证据1", "title": "灵山大佛"}]}),
                ("text", {"text": "灵山大佛高88米。[证据1]"}), *terminal)
            return httpx.Response(200, text=body, headers={"Content-Type": "text/event-stream"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await evaluate_remote_cases([mock_cases()[0]], endpoint="http://mock.local/stream", client=client)
    result = asyncio.run(scenario())[0]
    assert not result["checks"]["stream_completed"]
    assert not result["accuracy_pass"]


def test_latency_report_separates_complete_from_failed_streams():
    async def scenario():
        calls = 0
        async def handler(_request):
            nonlocal calls
            calls += 1
            if calls == 2:
                return httpx.Response(503, text="unavailable")
            return httpx.Response(200, text=response_for("只有最终文本"), headers={"Content-Type": "text/event-stream"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await evaluate_remote_cases(mock_cases()[:2], endpoint="http://mock.local/stream", client=client)
    results = asyncio.run(scenario())
    report = build_execution_report(mode="local-server", testset_path=Path("mock.json"),
                                    cases=mock_cases()[:2], results=results)
    assert report["latency_ms"]["total_all"]["count"] == 2
    assert report["latency_ms"]["total_completed"]["count"] == 1
    assert report["latency_ms"]["total_failed"]["count"] == 1
    assert report["latency_ms"]["first_text_completed"]["count"] == 1


def test_report_retains_backend_route_and_degraded_status():
    async def scenario():
        async def handler(_request):
            body = sse(("text", {"text": "回答"}), ("done", {
                "completion": "complete", "provider": "evidence_fallback",
                "hit_level": "rag_llm_fallback", "degraded": True}))
            return httpx.Response(200, text=body, headers={"Content-Type": "text/event-stream"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await evaluate_remote_cases([mock_cases()[0]], endpoint="http://mock.local/stream", client=client)
    results = asyncio.run(scenario())
    assert results[0]["provider"] == "evidence_fallback"
    assert results[0]["hit_level"] == "rag_llm_fallback"
    assert results[0]["degraded"] is True
    report = build_execution_report(mode="local-server", testset_path=Path("mock.json"),
                                    cases=mock_cases()[:1], results=results)
    assert report["route_summary"]["providers"]["evidence_fallback"] == 1
    assert report["route_summary"]["degraded"] == 1


def test_default_selection_preserves_sampled_real_prefix_and_local_limit():
    from eval.scripts.run_e2e_chat_eval import select_cases
    cases = load_cases(Path(__file__).resolve().parents[1] / 'testset' / 'e2e_qa_100.json')
    selected, metadata = select_cases(cases, mode='sampled-real')
    assert selected == cases[:5]
    assert metadata['method'] == 'head'
    assert metadata['seed'] is None
    selected, _ = select_cases(cases, mode='local-server', limit=3)
    assert selected == cases[:3]
    # Legacy dry-run validates the complete input even when --limit is supplied.
    selected, _ = select_cases(cases, mode='dry-run', limit=3)
    assert selected == cases


def test_stratified_selection_is_reproducible_balanced_and_input_order_independent():
    from collections import Counter
    from eval.scripts.run_e2e_chat_eval import select_cases
    cases = load_cases(Path(__file__).resolve().parents[1] / 'testset' / 'e2e_qa_100.json')
    selected, metadata = select_cases(cases, mode='sampled-real', limit=16, sampling='stratified', seed=37)
    repeated, _ = select_cases(list(reversed(cases)), mode='sampled-real', limit=16, sampling='stratified', seed=37)
    other, _ = select_cases(cases, mode='sampled-real', limit=16, sampling='stratified', seed=38)
    assert [item.id for item in selected] == [item.id for item in repeated]
    assert [item.id for item in selected] != [item.id for item in other]
    assert len({item.id for item in selected}) == 16
    assert set(Counter(item.category for item in selected).values()) == {2}
    assert metadata['selected_ids'] == [item.id for item in selected]
    assert metadata['selected_category_distribution'] == dict(Counter(item.category for item in selected))
    assert metadata['seed'] == 37
    assert metadata['method'] == 'category-balanced-round-robin-v1'


def test_stratified_small_sample_covers_distinct_categories_and_reports_missing_ones():
    from eval.scripts.run_e2e_chat_eval import select_cases
    cases = load_cases(Path(__file__).resolve().parents[1] / 'testset' / 'e2e_qa_100.json')
    selected, metadata = select_cases(cases, mode='sampled-real', sampling='stratified', seed=37)
    assert len(selected) == len({case.category for case in selected}) == 5
    assert len(metadata['omitted_categories']) == 3
    assert set(metadata['omitted_categories']).isdisjoint(case.category for case in selected)


def test_stratified_selection_handles_exhausted_strata_empty_and_zero_budget():
    from eval.scripts.run_e2e_chat_eval import select_cases
    cases = mock_cases()
    selected, metadata = select_cases(cases, mode='local-server', limit=99, sampling='stratified', seed=9)
    assert {item.id for item in selected} == {item.id for item in cases}
    assert len(selected) == 5
    assert metadata['effective_limit'] == 5
    for data, limit in (([], 10), (cases, 0)):
        selected, metadata = select_cases(data, mode='local-server', limit=limit, sampling='stratified')
        assert selected == []
        assert metadata['selected_ids'] == []


def test_stratified_dry_run_reports_exact_sample_without_network(monkeypatch, tmp_path):
    from eval.scripts import run_e2e_chat_eval as runner
    import sys
    output = tmp_path / 'stratified.json'
    testset = Path(__file__).resolve().parents[1] / 'testset' / 'e2e_qa_100.json'
    monkeypatch.setattr(sys, 'argv', ['runner', '--mode', 'dry-run', '--testset', str(testset),
        '--sampling', 'stratified', '--seed', '37', '--limit', '16', '--report', str(output)])
    def forbidden(*args, **kwargs):
        raise AssertionError('dry-run must not make HTTP requests')
    monkeypatch.setattr(runner.httpx, 'AsyncClient', forbidden)
    assert runner.main() == 0
    report = json.loads(output.read_text())
    assert report['case_count'] == 16
    assert report['selection']['seed'] == 37
    assert report['selection']['selected_ids'] == [case['id'] for case in report['cases']]
    assert len(report['selection']['testset_sha256']) == 64


def test_mock_remote_executes_exactly_the_ids_reported_by_the_single_selection(monkeypatch, tmp_path):
    from eval.scripts import run_e2e_chat_eval as runner
    import sys
    testset = Path(__file__).resolve().parents[1] / 'testset' / 'e2e_qa_100.json'
    output = tmp_path / 'remote-mock.json'
    monkeypatch.setattr(sys, 'argv', ['runner', '--mode', 'sampled-real', '--testset', str(testset),
        '--sampling', 'stratified', '--seed', '37', '--limit', '16', '--allow-network',
        '--endpoint', 'http://mock.local/api/chat/stream', '--report', str(output)])
    requests = []
    async def handler(request):
        payload = json.loads(request.content)
        requests.append(payload['query'])
        return httpx.Response(200, text=sse(('text', {'text': '仅用于离线模拟', 'is_complete': True}), ('done', {'completion': 'complete'})),
                              headers={'Content-Type': 'text/event-stream'})
    client_class = httpx.AsyncClient
    monkeypatch.setattr(runner.httpx, 'AsyncClient', lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    # Mock text intentionally does not satisfy the real knowledge assertions.
    assert runner.main() == 1
    report = json.loads(output.read_text())
    ids = report['selection']['selected_ids']
    assert len(ids) == len(requests) == 16
    assert ids == [result['id'] for result in report['results']]
    by_id = {case.id: case.query for case in load_cases(testset)}
    assert requests == [by_id[case_id] for case_id in ids]
    assert report['category_distribution'] == report['selection']['selected_category_distribution']


def test_sampling_never_bypasses_explicit_network_permission(monkeypatch, tmp_path):
    from eval.scripts import run_e2e_chat_eval as runner
    import sys
    output = tmp_path / 'denied.json'
    monkeypatch.setattr(sys, 'argv', ['runner', '--mode', 'sampled-real', '--sampling', 'stratified', '--report', str(output)])
    def forbidden(*args, **kwargs):
        raise AssertionError('no HTTP client without --allow-network')
    monkeypatch.setattr(runner.httpx, 'AsyncClient', forbidden)
    assert runner.main() == 2
    assert not output.exists()
