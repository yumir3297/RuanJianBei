from types import SimpleNamespace

import pytest


def _resolver_type():
    from app.services.qa.deterministic_answer_resolver import DeterministicAnswerResolver

    return DeterministicAnswerResolver


@pytest.mark.asyncio
async def test_unverified_schedule_has_priority_over_static_route():
    class RouteBuilder:
        calls = 0

        async def build_answer(self, request):
            self.calls += 1
            return "路线答案", [{"title": "预设路线"}]

    route_builder = RouteBuilder()
    resolver = _resolver_type()(route_builder=route_builder)

    decision = await resolver.resolve(
        SimpleNamespace(query="景区几点开门？"),
        vision_present=False,
        intent="static_route",
    )

    assert decision is not None
    assert decision.hit_level == "schedule_unverified"
    assert "无法核实最新开放或演出时间" in decision.answer
    assert decision.sources == []
    assert decision.status_text is None
    assert route_builder.calls == 0


@pytest.mark.asyncio
async def test_unverified_ticket_has_priority_over_static_route():
    class RouteBuilder:
        async def build_answer(self, request):
            raise AssertionError("static route must not override ticket uncertainty")

    resolver = _resolver_type()(route_builder=RouteBuilder())

    decision = await resolver.resolve(
        SimpleNamespace(query="门票多少钱？"),
        vision_present=False,
        intent="static_route",
    )

    assert decision is not None
    assert decision.hit_level == "ticket_unverified"
    assert "无法核实最新票价" in decision.answer


@pytest.mark.asyncio
async def test_static_route_requires_non_vision_static_route_intent():
    class RouteBuilder:
        calls = 0

        async def build_answer(self, request):
            self.calls += 1
            return "预设路线", [{"title": "路线"}]

    route_builder = RouteBuilder()
    resolver = _resolver_type()(route_builder=route_builder)
    request = SimpleNamespace(query="适合半天的路线")

    assert await resolver.resolve(request, vision_present=True, intent="static_route") is None
    assert await resolver.resolve(request, vision_present=False, intent="attraction_qa") is None
    assert route_builder.calls == 0

    decision = await resolver.resolve(request, vision_present=False, intent="static_route")

    assert decision is not None
    assert decision.hit_level == "static_route"
    assert decision.answer == "预设路线"
    assert decision.sources == [{"title": "路线"}]
    assert decision.status_text == "正在整理游览路线..."
    assert route_builder.calls == 1


@pytest.mark.asyncio
async def test_static_route_miss_falls_through_without_fast_answer():
    class RouteBuilder:
        async def build_answer(self, request):
            return None

    resolver = _resolver_type()(route_builder=RouteBuilder())

    assert await resolver.resolve(
        SimpleNamespace(query="帮我规划路线"),
        vision_present=False,
        intent="static_route",
    ) is None
