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
}

DYNAMIC_ROUTE_KEYWORDS = {
    "推荐路线",
    "规划路线",
    "怎么逛",
    "怎么玩",
    "顺路",
    "避开人流",
    "避开人群",
    "下雨",
    "天气",
    "客流",
    "拥挤",
    "实时",
    "动态",
    "亲子路线",
    "老人",
    "两小时",
    "半天",
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
            if selection.available_hours is not None or selection.avoid_crowded is True:
                return IntentDecision(
                    intent="dynamic_route",
                    confidence=0.9,
                    matched_keywords=("selection:route",),
                )
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
