from __future__ import annotations

from dataclasses import dataclass

from app.services.qa.guided_selector import ResolvedInteraction


@dataclass(frozen=True, slots=True)
class FollowUpSuggestion:
    label: str
    query: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "query": self.query}


class FollowUpSuggestionService:
    _ATTRACTION_TOPIC_TEMPLATES = {
        "history": ("继续了解历史", "{subject}有什么历史文化背景？"),
        "architecture": ("看看建筑特色", "{subject}有哪些建筑艺术特色？"),
        "blessing": ("了解祈福体验", "{subject}有哪些祈福体验？"),
        "family": ("查看亲子玩法", "带孩子游览{subject}有什么建议？"),
        "practical": ("获取实用信息", "参观{subject}有哪些实用信息？"),
        "dining": ("了解餐饮安排", "游览{subject}时餐饮可以怎样安排？"),
    }

    def generate(self, resolved: ResolvedInteraction) -> list[dict[str, str]]:
        suggestions = self._build_suggestions(resolved)
        unique: list[FollowUpSuggestion] = []
        seen_queries: set[str] = set()
        for suggestion in suggestions:
            if suggestion.query in seen_queries:
                continue
            seen_queries.add(suggestion.query)
            unique.append(suggestion)
        return [item.to_dict() for item in unique[:4]]

    def _build_suggestions(self, resolved: ResolvedInteraction) -> list[FollowUpSuggestion]:
        subject = resolved.active_subject
        mode = resolved.selection.mode

        if mode == "attraction" and subject:
            items: list[FollowUpSuggestion] = []
            topic_template = self._ATTRACTION_TOPIC_TEMPLATES.get(resolved.selection.topic_key or "")
            if topic_template:
                label, query = topic_template
                items.append(FollowUpSuggestion(label, query.format(subject=subject)))
            items.extend(
                [
                    FollowUpSuggestion("了解主要特色", f"{subject}有哪些主要特色？"),
                    FollowUpSuggestion("获取参观建议", f"参观{subject}时需要注意什么？"),
                    FollowUpSuggestion("了解游览时间", f"游览{subject}一般需要多长时间？"),
                ]
            )
            return items

        if mode == "topic" and subject:
            return [
                FollowUpSuggestion("查看代表景点", f"{subject}有哪些代表景点？"),
                FollowUpSuggestion("了解体验方式", f"在灵山胜境中可以怎样体验{subject}？"),
                FollowUpSuggestion("安排主题游览", f"围绕{subject}怎样安排游览？"),
            ]

        if mode == "route" and subject:
            return [
                FollowUpSuggestion("查看路线景点", f"{subject}包含哪些景点？"),
                FollowUpSuggestion("了解所需时间", f"{subject}大约需要多长时间？"),
                FollowUpSuggestion("查看适合人群", f"{subject}适合哪些游客？"),
                FollowUpSuggestion("获取路线提示", f"游览{subject}时需要注意什么？"),
            ]

        return [
            FollowUpSuggestion("看看主要景点", "灵山胜境有哪些主要景点？"),
            FollowUpSuggestion("规划首次游览", "第一次游览灵山胜境应该怎么安排？"),
            FollowUpSuggestion("获取实用建议", "灵山胜境有哪些实用游览建议？"),
        ]
