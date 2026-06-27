"""回答语气润色 — 为 FAQ / 缓存 / 无证据路径注入角色人设"""

from __future__ import annotations

# ── 角色开场前缀 ──

_OPENERS: dict[str, list[str]] = {
    "hanfu": [
        "好的，让我为您道来——",
        "嗯，这个问题问得好呢——",
        "来，咱们看看——",
        "根据官方资料记载——",
    ],
    "monk": [
        "善哉，容我一一道来——",
        "缘此——",
        "依记载所言——",
    ],
    "modern": [
        "好嘞，来看一下——",
        "没问题，这个问题——",
        "查到了——",
    ],
}

# ── 无证据拒答文案 ──

_NO_EVIDENCE: dict[str, str] = {
    "hanfu": (
        "这一点目前官方资料里还没有明确记载呢。"
        "您换个问法试试，或者直接选一个景区里的景点，我给您详细讲讲？"
    ),
    "monk": (
        "此事在现有资料中尚无记载。"
        "施主不妨换个问法，或先择一处景点，贫僧与你细讲。"
    ),
    "modern": (
        "目前资料里还没有这方面的信息哦。"
        "试试换个问法？或者选一个景点，我带你深入了解。"
    ),
}


def polish_answer(answer: str, persona: str | None, sources: list[dict]) -> str:
    """为 FAQ/缓存/无证据回答加上角色人设开场语。

    不做任何事实改动，只在回答前加一句自然开场。
    如果答案本身已经带有人味（含"您""咱们""呢"等语气词），不再重复添加。
    """
    key = persona or "hanfu"
    if _has_human_tone(answer):
        return answer
    opener = _pick_opener(key, answer)
    if not opener:
        return answer
    return f"{opener} {answer}"


def no_evidence_reply(persona: str | None) -> str:
    """返回角色人设化的无证据拒答文案。"""
    key = persona or "hanfu"
    return _NO_EVIDENCE.get(key, _NO_EVIDENCE["hanfu"])


def _has_human_tone(text: str) -> bool:
    """判断回答是否已经带了人味语气词。"""
    human_markers = ("您", "咱们", "呢", "哦", "啦", "善哉", "缘此", "好嘞", "吧")
    return any(m in text for m in human_markers)


def _pick_opener(persona_key: str, answer: str) -> str:
    """从开场词库中轮转选择，避免每题都讲同一句。"""
    import hashlib
    openers = _OPENERS.get(persona_key, _OPENERS["hanfu"])
    idx = int(hashlib.md5(answer[:40].encode()).hexdigest()[:4], 16) % len(openers)
    return openers[idx]
