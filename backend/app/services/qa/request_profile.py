from __future__ import annotations

from app.schemas.chat import ChatRequest


_LINGSHAN_ATTRACTIONS = [
    "灵山大佛", "大佛", "灵山梵宫", "梵宫", "九龙灌浴", "五印坛城",
    "坛城", "五明桥", "五智门", "五灯湖", "佛教文化博览馆", "佛足坛",
    "拈花堂", "拈花广场", "无尽意斋", "曼飞龙塔", "梵天花海",
    "大照壁", "灵山大照壁", "百子戏弥勒", "祥符禅寺",
    "菩提大道", "阿育王柱", "降魔浮雕", "香月花街", "鹿鸣谷",
    "灵山胜境", "灵山",
]

_PERSONA_AUDIENCE_MAP = {"hanfu": "culture", "monk": "culture", "modern": "free"}
_TOPIC_AUDIENCE_HINTS = {
    "family": "family", "blessing": "culture", "history": "culture",
    "architecture": "culture", "routes": "free", "dining": "leisure",
    "practical": "general",
}


def infer_audience_type(request: ChatRequest) -> str:
    selection = request.selection
    if selection is not None:
        if selection.audience_type:
            return selection.audience_type
        if selection.mode == "topic" and selection.topic_key:
            return _TOPIC_AUDIENCE_HINTS.get(selection.topic_key, "general")
    if request.persona:
        return _PERSONA_AUDIENCE_MAP.get(request.persona, "general")
    return "general"


def extract_interests(request: ChatRequest) -> list[str]:
    interests: list[str] = []
    selection = request.selection
    if selection is not None and selection.interests:
        interests.extend(selection.interests)
    for attraction in _LINGSHAN_ATTRACTIONS:
        if attraction in request.query and attraction not in interests:
            interests.append(attraction)
    return interests[:8]


def resolve_narration_audience(request: ChatRequest) -> str:
    """Resolve child/adult/expert narration without promoting route styles to expert."""
    if request.audience:
        return request.audience
    return "child" if infer_audience_type(request) == "family" else "adult"
