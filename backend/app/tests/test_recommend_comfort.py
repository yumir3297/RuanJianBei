import json
from types import SimpleNamespace

from app.schemas.recommend import RecommendRequest
from app.services.recommend.engine import RecommendEngine


class DummyRouteRepository:
    def list_all(self):
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
    engine = RecommendEngine(DummyRouteRepository())

    response = engine.generate(
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
    assert "\u4f18\u5148\u9009\u62e9\u8f83\u77ed\u8def\u7ebf\u4e0e\u5ba4\u5185\u505c\u7559\u70b9" in route.reason


def test_rain_is_inferred_from_weather_condition() -> None:
    engine = RecommendEngine(DummyRouteRepository())

    response = engine.generate(
        RecommendRequest(
            session_id="rain-demo",
            weather_condition="\u5c0f\u96e8",
        )
    )

    assert response.routes[0].route_id == "route_003"
    assert "\u96e8\u5929\u9002\u914d" in response.routes[0].comfort_tags
