from app.schemas.selection import SelectionContext
from app.services.qa.intent_router import IntentRouter


def test_intent_router_detects_dynamic_route_keywords() -> None:
    decision = IntentRouter().detect("请根据天气和客流帮我规划路线")

    assert decision.intent == "dynamic_route"
    assert decision.confidence >= 0.7
    assert "天气" in decision.matched_keywords


def test_intent_router_uses_route_selection_context() -> None:
    decision = IntentRouter().detect(
        "帮我看看这条路线",
        SelectionContext(mode="route", route_id="route_001", available_hours=2, avoid_crowded=True),
    )

    assert decision.intent == "dynamic_route"
    assert decision.confidence == 0.9


def test_intent_router_falls_back_to_static_qa() -> None:
    decision = IntentRouter().detect("灵山大佛有多高")

    assert decision.intent == "static_qa"
