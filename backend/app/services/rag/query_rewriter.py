from __future__ import annotations

import re

from app.schemas.chat import ConversationContext


class QueryRewriter:
    def __init__(self) -> None:
        self.alias_map = {
            "大佛": "灵山大佛",
            "那个大佛": "灵山大佛",
            "那座塔": "五印坛城",
        }
        self.replacements = {
            "啥时候": "时间",
            "来着": "",
            "多少来着": "多少",
            "那个": "",
            "请问": "",
        }

    def rewrite(self, raw_query: str, context: ConversationContext | None = None) -> str:
        normalized = raw_query.strip()
        for src, target in self.alias_map.items():
            normalized = normalized.replace(src, target)
        for src, target in self.replacements.items():
            normalized = normalized.replace(src, target)

        normalized = re.sub(r"[？?！!，,。]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if context and context.last_subject and context.last_subject not in normalized:
            if normalized.startswith(("多高", "多长", "时间", "什么时候")):
                normalized = f"{context.last_subject} {normalized}"

        return normalized or raw_query.strip()

