from __future__ import annotations

from dataclasses import dataclass

from app.schemas.selection import SelectionContext


# 预设路线关键词：全部路线诉求统一走“后端预设路线”口径，不再区分动态/静态。
# 原 dynamic_route 关键词（天气、客流、避峰、时长等）并入此表，由 RecommendEngine
# 按偏好从预设路线模板中选取，不再依赖外部编排服务。
ROUTE_KEYWORDS = {
    "路线",
    "路线推荐",
    "推荐路线",
    "规划路线",
    "线路",
    "游览线",
    "游览路线",
    "攻略",
    "怎么走",
    "怎么逛",
    "一日游",
    "半日",
    "朝圣",
    "带老人",
    "带小孩",
    "亲子游",
    "亲子路线",
    "老人",
    "避开人流",
    "避开人群",
    "避峰",
    "下雨",
    "天气",
    "客流",
    "拥挤",
    "实时",
    "动态",
    "三个小时",
    "3个小时",
    "半天",
    "帮我规划",
    "推荐",
    "两小时",
    "2小时",
    "一小时",
    "1小时",
}


@dataclass(frozen=True, slots=True)
class IntentDecision:
    intent: str
    confidence: float
    matched_keywords: tuple[str, ...] = ()


class IntentRouter:
    """把游客提问归类为“预设路线”或“景区问答”两类。"""

    def detect(self, query: str, selection: SelectionContext | None = None) -> IntentDecision:
        normalized = (query or "").strip()
        if not normalized:
            return IntentDecision(intent="static_qa", confidence=0.0)

        # 主动选择了“规划路线”模式：直接进入预设路线分支。
        if selection is not None and selection.mode == "route":
            return IntentDecision(
                intent="static_route",
                confidence=0.9,
                matched_keywords=("selection:route",),
            )

        route_hits = tuple(keyword for keyword in ROUTE_KEYWORDS if keyword in normalized)
        if route_hits:
            confidence = 0.85 if len(route_hits) >= 2 else 0.7
            return IntentDecision(
                intent="static_route",
                confidence=confidence,
                matched_keywords=route_hits,
            )

        return IntentDecision(intent="static_qa", confidence=0.55)
