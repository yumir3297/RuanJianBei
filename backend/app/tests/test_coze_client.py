import asyncio

import httpx
import pytest

from app.services.coze.client import CozeRoutePlanner, CozeRoutePlannerError


def test_coze_client_parses_result_json_string() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://example.com/run")
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "result_json": {
                    "answer": "推荐先游梵宫，再去大佛。",
                    "route_stops": [{"attraction_id": "13", "reason": "顺路"}],
                    "adjustments": ["当前客流中等，建议错峰"],
                    "sources": ["官方路线候选", "实时上下文"],
                    "warning": "",
                    "live_data_timestamp": "2026-07-15T10:00:00+08:00",
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    planner = CozeRoutePlanner(
        run_url="https://example.com/run",
        token="token",
        http_client=client,
    )

    plan = asyncio.run(planner.run({"question": "test"}))
    asyncio.run(client.aclose())

    assert plan.answer.startswith("推荐先游")
    assert plan.route_stops[0]["attraction_id"] == "13"


def test_coze_client_rejects_invalid_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"result_json": {"route_stops": []}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    planner = CozeRoutePlanner(
        run_url="https://example.com/run",
        token="token",
        http_client=client,
    )

    with pytest.raises(CozeRoutePlannerError):
        asyncio.run(planner.run({"question": "test"}))

    asyncio.run(client.aclose())


def test_coze_client_parses_nested_route_stops() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "result_json": {
                    "answer": "推荐先游大佛，再去梵宫。当前天气晴、客流中等为演示模拟数据。",
                    "warning": "",
                    "route": {
                        "id": "1",
                        "name": "经典路线",
                        "duration": "3小时",
                        "route_stops": [
                            {"attraction_id": "1", "name": "大佛", "reason": "适合文化体验", "status": "开放"},
                            {"attraction_id": "13", "name": "梵宫", "reason": "适合错峰参观", "status": "开放"},
                        ],
                    },
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    planner = CozeRoutePlanner(
        run_url="https://example.com/run",
        token="token",
        http_client=client,
    )

    plan = asyncio.run(planner.run({"question": "test"}))
    asyncio.run(client.aclose())

    assert plan.answer.startswith("推荐先游")
    assert len(plan.route_stops) == 2
    assert plan.route_stops[0]["attraction_id"] == "1"
    assert plan.route_stops[1]["attraction_id"] == "13"
    assert plan.adjustments == []
    assert plan.sources == []
