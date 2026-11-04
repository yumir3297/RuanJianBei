import asyncio
from types import SimpleNamespace

from app.schemas.chat import ChatRequest
from app.schemas.selection import SelectionContext
from app.services.qa.route_fast_path import StaticRouteAnswerBuilder


class Routes:
    async def list_all(self):
        return [SimpleNamespace(
            id="family-2h",
            title="亲子轻松线",
            duration_label="2小时",
            route_plan="入口 → 灵山大佛 → 梵宫",
            source="景区预设路线",
            tags="亲子|家庭",
        )]


def test_static_route_builder_keeps_deterministic_route_and_budget_conflict_paths():
    builder = StaticRouteAnswerBuilder(Routes())

    async def scenario():
        answer, sources = await builder.build_answer(ChatRequest(
            query="推荐亲子路线",
            session_id="route-fast-path",
            selection=SelectionContext(mode="route", available_hours=2),
        ))
        assert "亲子轻松线" in answer
        assert "入口 → 灵山大佛 → 梵宫" in answer
        assert sources[0]["source"] == "景区预设路线"

        conflict = await builder.build_answer(ChatRequest(
            query="推荐2小时亲子路线",
            session_id="route-budget-conflict",
            selection=SelectionContext(mode="route", available_hours=4),
        ))
        assert conflict is not None
        assert "时间预算" in conflict[0]
        assert conflict[1] == []

    asyncio.run(scenario())
