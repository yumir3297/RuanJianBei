"""把结构化游客记忆渲染成可注入 system prompt 的短文本。

设计约束：
- 这是"语气与信息顺序"的输入，不是景区事实来源；
- 必须短（默认 ≤ 8 个景点），避免挤占证据预算；
- 首访且无任何信号时返回空串，不产生任何 system prompt 噪声。
"""

from __future__ import annotations

AUDIENCE_PREFERENCE_LABEL: dict[str, str] = {
    "child": "希望用孩子能听懂的方式讲解",
    "expert": "希望听到更专业、更深入的细节",
}

MAX_ATTRACTIONS_IN_PROMPT = 8
MAX_TAGS_IN_PROMPT = 6


def build_memory_prompt(
    memory: dict | None,
    *,
    max_attractions: int = MAX_ATTRACTIONS_IN_PROMPT,
    max_tags: int = MAX_TAGS_IN_PROMPT,
) -> str:
    if not memory:
        return ""

    visit_count = int(memory.get("visit_count") or 0)
    attractions = [
        str(item) for item in (memory.get("visited_attractions") or []) if str(item).strip()
    ]
    tags = [str(item) for item in (memory.get("preference_tags") or []) if str(item).strip()]

    has_attractions = bool(attractions)
    has_tags = bool(tags)
    if visit_count < 2 and not has_attractions and not has_tags:
        return ""

    lines: list[str] = ["【游客记忆】"]
    if visit_count >= 2:
        lines.append(f"这位游客是第 {visit_count} 次来到本景区，可在合适时机自然地说一句欢迎回来。")
    if has_attractions:
        lines.append("已经游览过：" + "、".join(attractions[:max_attractions]) + "。")
    if has_tags:
        lines.append("关注点：" + "、".join(tags[:max_tags]) + "。")

    preference = AUDIENCE_PREFERENCE_LABEL.get(str(memory.get("narration_audience") or ""), "")
    if preference:
        lines.append(f"讲解偏好：{preference}。")

    lines.append(
        "以上记忆只用于调整语气与信息顺序；不要把记忆当作景区事实依据，也不要生硬复述整份记录。"
    )
    return "\n".join(lines)
