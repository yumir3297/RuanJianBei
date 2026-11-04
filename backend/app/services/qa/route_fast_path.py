from __future__ import annotations

from app.schemas.chat import ChatRequest
from app.schemas.recommend import RecommendRequest
from app.services.qa.route_constraints import explicit_route_hours
from app.services.qa.request_profile import extract_interests, infer_audience_type
from app.services.recommend.engine import RecommendEngine


class StaticRouteAnswerBuilder:
    """Deterministic answer builder for the known-route fast path."""

    def __init__(self, route_repository) -> None:
        self.route_repository = route_repository

    async def build_answer(self, request: ChatRequest) -> tuple[str, list[dict]] | None:
        if self.route_repository is None:
            return None
        routes = await self.route_repository.list_all()
        if not routes:
            return None

        budget = request.selection.available_hours if request.selection else None
        query_budget = explicit_route_hours(request.query)
        if budget is not None and query_budget is not None and budget != query_budget:
            return (f"当前选择的时间是{budget}小时，问题中是{query_budget}小时；请确认时间预算，重新选择或清除之前的时间设置后再提问。", [])
        if budget is None:
            budget = query_budget
        no_known_fit = False
        if budget is not None:
            fitting = [route for route in routes
                       if (hours := RecommendEngine._duration_hours(route.duration_label, budget)) is not None
                       and hours <= budget]
            if fitting:
                routes = fitting
            else:
                no_known_fit = True

        def pick(*keywords: str):
            return next((route for route in routes
                         if any(keyword in route.title or keyword in getattr(route, "tags", "") for keyword in keywords)), None)

        normalized = (request.query or "").strip()
        is_point_to_point = (
            "大佛" in normalized and "梵宫" in normalized
            and any(marker in normalized for marker in ("怎么走", "怎么去", "从", "到"))
        )
        if is_point_to_point:
            selected = next((route for route in routes if "大佛" in route.route_plan and "梵宫" in route.route_plan), routes[0])
            answer = (
                f"可参考预设路线：{selected.route_plan}。"
                "此路线未核验两点之间的实际通路；如需少走路，可向服务台确认当日安排。"
            )
        else:
            selected = None
            if any(marker in normalized for marker in ("小孩", "孩子", "亲子")):
                selected = pick("亲子")
            elif any(marker in normalized for marker in ("建筑", "佛教", "文化", "朝圣")):
                selected = pick("历史", "文化")
            elif any(marker in normalized for marker in ("自然", "风景", "免费")):
                selected = pick("自然")
            elif any(marker in normalized for marker in ("老人", "省力", "半天", "3个小时", "三个小时")):
                selected = pick("亲子", "自然")
            if selected is None:
                selected = await self._select_preset_route(routes, request)
            selected = selected or routes[0]

            route_plan = selected.route_plan
            if any(marker in normalized for marker in ("3个小时", "三个小时")):
                stops = [item.strip() for item in route_plan.split("→") if item.strip()]
                route_plan = " → ".join(stops[:4])
                answer = f"可参考路线中的前几个景点：{route_plan}。时间紧时优先看核心景点，其余景点可根据现场时间灵活取舍。"
            elif "半天" in normalized:
                answer = f"半天可参考{selected.title}（{selected.duration_label}）：{route_plan}。建议提前入园，并按现场演出时间和体力情况删减停留点。"
            elif "一日" in normalized or "全天" in normalized:
                answer = f"一日游建议以{selected.title}为主线：{route_plan}。上午安排核心景点，下午可继续游览沿线文化场馆与特色建筑，并预留休息与用餐时间。"
            else:
                answer = f"推荐{selected.title}（{selected.duration_label}）：{route_plan}。"

        if no_known_fit:
            answer = f"暂无标注时长符合{budget}小时预算的预设路线。以下仅供调整参考：{answer}"
        elif budget is None and ("小时" in normalized or "半天" in normalized):
            answer = "未能确定具体时间预算，请核对可用时间后再选择。" + answer
        answer += " 这是预设路线，未结合实时路况或客流，实际时长和开放情况请以现场信息为准。"
        sources = [{
            "evidence_id": "路线1", "title": selected.title,
            "snippet": selected.route_plan, "source": selected.source,
        }]
        return answer, sources

    async def _select_preset_route(self, routes, request: ChatRequest):
        selection = request.selection
        requested_hours = selection.available_hours if selection and selection.available_hours else 4
        recommend_request = RecommendRequest(
            session_id=request.session_id,
            interests=extract_interests(request),
            available_hours=min(max(int(requested_hours), 1), 12),
            audience_type=infer_audience_type(request),
            avoid_crowded=bool(selection.avoid_crowded) if selection else False,
        )
        response = await RecommendEngine(self.route_repository).generate(recommend_request)
        if not response.routes:
            return None
        target_id = response.routes[0].route_id
        return next((route for route in routes if route.id == target_id), None)
