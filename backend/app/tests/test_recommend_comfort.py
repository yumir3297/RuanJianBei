import asyncio
import json
from types import SimpleNamespace

from app.schemas.recommend import RecommendRequest
from app.services.recommend.engine import RecommendEngine


class DummyRouteRepository:
    async def list_all(self):
        return [
            self._route("route_001", "history", "6 hours"),
            self._route("route_002", "nature", "5 hours"),
            self._route("route_003", "family", "4 hours"),
        ]

    @staticmethod
    def _route(route_id: str, title: str, duration: str):
        return SimpleNamespace(
            id=route_id,
            title=title,
            duration_label=duration,
            route_plan="entrance -> indoor hall -> exit",
            guide_points_json=json.dumps(["official guide"]),
            experiences_json=json.dumps(["indoor stop"]),
            source="official",
        )


def test_hot_weather_selects_short_comfort_route_with_explanation() -> None:
    async def scenario():
        engine = RecommendEngine(DummyRouteRepository())

        response = await engine.generate(
            RecommendRequest(
                session_id="comfort-demo",
                interests=["culture"],
                available_hours=5,
                comfort_preferences=["avoid_heat", "less_walking"],
                weather_condition="sunny",
                temperature_c=34,
            )
        )

        route = response.routes[0]
        assert route.route_id == "route_003"
        assert route.comfort_tags == ["\u51cf\u5c11\u66b4\u6652", "\u5c11\u8d70\u8def", "\u9ad8\u6e29\u907f\u6691"]
        assert "现场" in route.reason

    asyncio.run(scenario())


def test_duration_is_not_truncated_to_available_budget():
    assert RecommendEngine._duration_hours("3.5-4小时全景", 2) == 4
    assert RecommendEngine._duration_hours("2.5小时", 2) == 3


def test_alternative_is_not_described_as_low_crowd_without_data():
    reason = RecommendEngine._build_reason("路线", RecommendRequest(session_id="test", avoid_crowded=True), alternative=True)
    assert "低拥挤" not in reason


def test_rain_is_inferred_from_weather_condition() -> None:
    async def scenario():
        engine = RecommendEngine(DummyRouteRepository())

        response = await engine.generate(
            RecommendRequest(
                session_id="rain-demo",
                weather_condition="\u5c0f\u96e8",
            )
        )

        assert response.routes[0].route_id == "route_003"
        assert "\u96e8\u5929\u9002\u914d" in response.routes[0].comfort_tags

    asyncio.run(scenario())
