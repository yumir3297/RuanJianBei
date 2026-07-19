from __future__ import annotations

import json
import re

from app.repositories.route import RouteRepository
from app.schemas.recommend import RecommendItem, RecommendRequest, RecommendResponse


class RecommendEngine:
    def __init__(self, route_repository: RouteRepository) -> None:
        self.route_repository = route_repository

    async def generate(self, request: RecommendRequest) -> RecommendResponse:
        routes = await self.route_repository.list_all()
        if not routes:
            return RecommendResponse(routes=[])

        primary_route = self._select_primary_route(routes, request)
        items = [self._build_item(primary_route, request, alternative=False)]

        if request.avoid_crowded:
            alternative_route = self._select_alternative_route(routes, primary_route.id)
            if alternative_route is not None:
                items.append(self._build_item(alternative_route, request, alternative=True))

        return RecommendResponse(routes=items)

    def _select_primary_route(self, routes, request: RecommendRequest):
        interests = " ".join(request.interests)
        audience_type = request.audience_type.strip().lower()

        # Lightweight, explainable comfort rules for the competition demo.
        # route_003 is the shortest official template and contains more indoor
        # stops, so it is a safe default for heat, rain and low-walking needs.
        comfort = set(request.comfort_preferences)
        weather = (request.weather_condition or "").lower()
        needs_comfort_route = bool(
            comfort.intersection({"avoid_heat", "less_walking", "family", "senior", "rain"})
            or (request.temperature_c is not None and request.temperature_c >= 30)
            or any(marker in weather for marker in ("rain", "storm", "雨", "雷"))
        )
        if needs_comfort_route:
            route = self._find_by_id(routes, "route_003")
            if route is not None:
                return route

        if any(keyword in interests for keyword in ("亲子", "孩子", "家庭")) or audience_type == "family":
            route = self._find_by_id(routes, "route_003")
            if route is not None:
                return route

        if any(keyword in interests for keyword in ("自然", "风光")):
            route = self._find_by_id(routes, "route_002")
            if route is not None:
                return route

        if any(keyword in interests for keyword in ("历史", "文化")):
            route = self._find_by_id(routes, "route_001")
            if route is not None:
                return route

        return self._find_by_id(routes, "route_001") or routes[0]

    @staticmethod
    def _select_alternative_route(routes, selected_id: str):
        for route in routes:
            if route.id != selected_id:
                return route
        return None

    @staticmethod
    def _find_by_id(routes, route_id: str):
        for route in routes:
            if route.id == route_id:
                return route
        return None

    def _build_item(self, route, request: RecommendRequest, *, alternative: bool) -> RecommendItem:
        guide_points = json.loads(route.guide_points_json)
        experiences = json.loads(route.experiences_json)
        title_prefix = "备选" if alternative else "推荐"
        reason = self._build_reason(route.title, request, alternative=alternative)
        return RecommendItem(
            route_id=route.id,
            title=f"{title_prefix}：{route.title}",
            reason=reason,
            duration_hours=self._duration_hours(route.duration_label, request.available_hours),
            duration_label=route.duration_label,
            route_plan=route.route_plan,
            guide_points=guide_points,
            experiences=experiences,
            comfort_tags=self._comfort_tags(request),
            source=route.source,
        )

    @staticmethod
    def _duration_hours(duration_label: str, available_hours: int) -> int:
        match = re.search(r"(\d+)", duration_label)
        if not match:
            return max(1, available_hours)
        return min(int(match.group(1)), available_hours)

    @staticmethod
    def _build_reason(route_title: str, request: RecommendRequest, *, alternative: bool) -> str:
        interests = "、".join(request.interests) if request.interests else "综合游览"
        audience = request.audience_type or "general"
        base = f"根据 {interests} 兴趣、{request.available_hours} 小时可用时间和 {audience} 人群偏好，匹配到 {route_title}。"
        comfort_tags = RecommendEngine._comfort_tags(request)
        if comfort_tags:
            base = f"{base} 已结合{'、'.join(comfort_tags)}需求，优先选择较短路线与室内停留点。"
        if alternative:
            return f"{base} 这条路线作为低拥挤或备选方案返回，方便现场二次选择。"
        return base

    @staticmethod
    def _comfort_tags(request: RecommendRequest) -> list[str]:
        labels = {
            "avoid_heat": "减少暴晒",
            "less_walking": "少走路",
            "family": "亲子/老人友好",
            "senior": "老人友好",
            "rain": "雨天适配",
        }
        tags = [labels[item] for item in request.comfort_preferences if item in labels]
        weather = request.weather_condition or ""
        if request.temperature_c is not None and request.temperature_c >= 30 and "高温避暑" not in tags:
            tags.append("高温避暑")
        if any(marker in weather for marker in ("雨", "雷", "rain", "storm")) and "雨天适配" not in tags:
            tags.append("雨天适配")
        return tags
