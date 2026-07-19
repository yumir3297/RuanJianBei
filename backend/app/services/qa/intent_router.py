from __future__ import annotations

from dataclasses import dataclass

from app.schemas.selection import SelectionContext


STATIC_ROUTE_KEYWORDS = {
    "路线",
    "路线推荐",
    "线路",
    "游览线",
    "游览路线",
    "攻略",
    "怎么走",
    "怎么逛",
    "一日游",
    "朝圣",
    "带老人",
    "带小孩",
    "亲子游",
}

DYNAMIC_ROUTE_KEYWORDS = {
    "推荐路线",
    "规划路线",
    "怎么逛",
    "怎么走",
    "避开人流",
    "避开人群",
    "下雨",
    "天气",
    "客流",
    "拥挤",
    "实时",
    "动态",
    "亲子路线",
    "带小孩",
    "老人",
    "三个小时",
    "3个小时",
    "半天",
    "一日游",
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

    @property
    def is_dynamic_route(self) -> bool:
        return self.intent == "dynamic_route"


class IntentRouter:
    def detect(self, query: str, selection: SelectionContext | None = None) -> IntentDecision:
        normalized = (query or "").strip()
        if not normalized:
            return IntentDecision(intent="static_qa", confidence=0.0)

        if selection is not None and selection.mode == "route":
            # 先检查查询是否包含动态路线关键词（如"避开人流"、"帮我规划"等）
            dynamic_hits = tuple(keyword for keyword in DYNAMIC_ROUTE_KEYWORDS if keyword in normalized)
            if dynamic_hits:
                return IntentDecision(
                    intent="dynamic_route",
                    confidence=0.9,
                    matched_keywords=dynamic_hits + ("selection:route",),
                )
            # 或者 selection 本身触发了动态条件
            if selection.available_hours is not None or selection.avoid_crowded is True:
                return IntentDecision(
                    intent="dynamic_route",
                    confidence=0.9,
                    matched_keywords=("selection:route",),
                )
            # 否则走静态路线
            return IntentDecision(
                intent="static_route",
                confidence=0.8,
                matched_keywords=("selection:route",),
            )

        dynamic_hits = tuple(keyword for keyword in DYNAMIC_ROUTE_KEYWORDS if keyword in normalized)
        if dynamic_hits:
            confidence = 0.85 if len(dynamic_hits) >= 2 else 0.7
            return IntentDecision(
                intent="dynamic_route",
                confidence=confidence,
                matched_keywords=dynamic_hits,
            )

        static_hits = tuple(keyword for keyword in STATIC_ROUTE_KEYWORDS if keyword in normalized)
        if static_hits:
            return IntentDecision(
                intent="static_route",
                confidence=0.7,
                matched_keywords=static_hits,
            )

        return IntentDecision(intent="static_qa", confidence=0.55)