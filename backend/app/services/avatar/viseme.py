"""基于拼音的中文口型（viseme）映射。

将文字转为拼音 → 韵母映射到 5 种开口等级 → 生成带缓动的帧时间线。
不依赖真实音频分析，但比纯随机循环接近真实发音规律。
"""

from __future__ import annotations

from typing import Sequence

# 尝试导入 pypinyin Style 枚举
try:
    from pypinyin import Style as _PinyinStyle
    _FINALS_STYLE = _PinyinStyle.FINALS       # 值 = 5
    _NORMAL_STYLE = _PinyinStyle.NORMAL        # 值 = 0
    _PINYIN_AVAILABLE = True
except ImportError:
    _FINALS_STYLE = None
    _NORMAL_STYLE = None
    _PINYIN_AVAILABLE = False


# ── 韵母 → 开口等级 (0=闭 到 1=大开) ──
# 等级参考：a/e/i/o/u/ü 在中文中对应的实际开口度
_VOWEL_TO_OPENNESS: dict[str, float] = {
    # a 系 — 大开口
    "a": 0.85, "ia": 0.80, "ua": 0.80,
    "ai": 0.75, "uai": 0.70,
    "ao": 0.72, "iao": 0.68,
    "an": 0.70, "ian": 0.65, "uan": 0.65, "üan": 0.62, "van": 0.62,
    "ang": 0.78, "iang": 0.72, "uang": 0.72,
    # o/e 系 — 中等开口
    "o": 0.55, "uo": 0.50,
    "e": 0.52, "ie": 0.48, "üe": 0.45, "ve": 0.45,
    "ei": 0.42, "uei": 0.40, "ui": 0.40,
    "ou": 0.48, "iou": 0.44, "iu": 0.44,
    "en": 0.38, "uen": 0.35, "un": 0.35,
    "eng": 0.40, "ueng": 0.38,
    "ong": 0.42, "iong": 0.38,
    # i/u/ü 系 — 小开口 (pypinyin 用 v 表示 ü)
    "i": 0.22, "in": 0.20, "ing": 0.18,
    "u": 0.18,
    "ü": 0.20, "v": 0.20, "ün": 0.18, "vn": 0.18,
    # er — 中等
    "er": 0.45,
}
_VOWEL_FALLBACK = 0.38  # 未知韵母时的默认中等开口

# ── 韵母 → 口型圆展度 (0=展唇/咧开, 1=圆唇/噘嘴) ──
_VOWEL_TO_ROUNDNESS: dict[str, float] = {
    # 圆唇音
    "o": 0.85, "uo": 0.82,
    "u": 0.90, "ou": 0.75, "iou": 0.72, "iu": 0.72,
    "ong": 0.70, "iong": 0.68,
    "ao": 0.50, "iao": 0.45,
    "ü": 0.78, "v": 0.78, "üe": 0.75, "ve": 0.75, "üan": 0.70, "van": 0.70, "ün": 0.72, "vn": 0.72,
    # 展唇音
    "a": 0.10, "ia": 0.08, "ua": 0.08,
    "ai": 0.05, "uai": 0.05,
    "an": 0.08, "ian": 0.06, "uan": 0.06,
    "ang": 0.10, "iang": 0.08, "uang": 0.08,
    "e": 0.12, "ie": 0.10, "ei": 0.08, "uei": 0.06, "ui": 0.06,
    "en": 0.10, "uen": 0.08, "un": 0.08,
    "eng": 0.10, "ueng": 0.08,
    "i": 0.20, "in": 0.18, "ing": 0.16,
    "er": 0.15,
}
_ROUNDNESS_FALLBACK = 0.15

# ── 韵母 → 时长权重 ──
# 复韵母/鼻韵母比单韵母长
_VOWEL_DURATION_WEIGHT: dict[str, float] = {
    "a": 1.0, "o": 1.0, "e": 1.0, "i": 0.8, "u": 0.8, "ü": 0.8, "v": 0.8,
    "ai": 1.3, "ei": 1.2, "ao": 1.3, "ou": 1.2,
    "ia": 1.2, "ie": 1.1, "ua": 1.2, "uo": 1.1, "üe": 1.1, "ve": 1.1,
    "iao": 1.4, "iou": 1.3, "iu": 1.3, "uai": 1.3, "uei": 1.3, "ui": 1.3,
    "an": 1.2, "en": 1.1, "ian": 1.3, "uan": 1.2, "üan": 1.3, "van": 1.3,
    "ang": 1.3, "eng": 1.2, "iang": 1.4, "uang": 1.3, "ueng": 1.3,
    "ong": 1.2, "iong": 1.3,
    "in": 1.0, "ing": 1.1, "un": 1.0, "ün": 1.0, "vn": 1.0,
    "er": 1.2,
}
_DEFAULT_WEIGHT = 1.0

# ── 闭口辅音（声母）→ 极低开口度 ──
_CLOSED_CONSONANTS = frozenset({"b", "p", "m", "f"})


def get_viseme_openness(pinyin_final: str) -> float:
    """根据拼音韵母返回开口度 0-1。"""
    final = pinyin_final.lstrip("'").rstrip("0123456789")
    if not final:
        return 0.05
    return _VOWEL_TO_OPENNESS.get(final, _VOWEL_FALLBACK)


def get_viseme_roundness(pinyin_final: str) -> float:
    """根据拼音韵母返回圆展度 0-1。"""
    final = pinyin_final.lstrip("'").rstrip("0123456789")
    if not final:
        return 0.05
    return _VOWEL_TO_ROUNDNESS.get(final, _ROUNDNESS_FALLBACK)


def get_duration_weight(pinyin_final: str) -> float:
    """返回该韵母相对于基准时长的权重。"""
    final = pinyin_final.lstrip("'").rstrip("0123456789")
    return _VOWEL_DURATION_WEIGHT.get(final, _DEFAULT_WEIGHT)


def is_closed_initial(pinyin: str) -> bool:
    """判断拼音声母是否为闭口音 (b p m f)。"""
    clean = pinyin.lstrip("'")
    if len(clean) >= 2 and clean[:2] in ("ch", "sh", "zh"):
        return False
    return clean[:1] in _CLOSED_CONSONANTS


def build_viseme_timeline(
    text: str,
    duration_ms: int,
    *,
    pinyin_fn=None,
) -> list[dict]:
    """根据中文文字生成改进的口型时间线。

    每个非空白字 → 拼音 → 开口度 + 圆展度 + 时长权重。
    结果按权重分配时长，相邻相同开口度的帧合并，帧间线性缓动。

    Returns:
        [{"start": ms, "end": ms, "value": float, "form": float}, ...]
    """
    # 去掉空白，保留可显示字符
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return []

    # 标点集合
    punctuation = set("，。！？；：、,.!?;:""''（）()【】[]{}《》<>…—")

    # ── 先估算每个字的开口度和时长权重 ──
    frame_specs: list[dict] = []
    for char in chars:
        if char in punctuation:
            frame_specs.append({"char": char, "openness": 0.0, "roundness": 0.0, "weight": 0.35, "is_punct": True})
            continue

        pinyin = ""
        final = ""
        try:
            if pinyin_fn is not None:
                results = pinyin_fn(char, heteronym=False, style=_FINALS_STYLE)
                if results:
                    final = str(results[0][0]) if isinstance(results[0], list) else str(results[0])
                # 顺便取带声母的全拼
                full_results = pinyin_fn(char, heteronym=False, style=_NORMAL_STYLE)
                if full_results:
                    pinyin = str(full_results[0][0]) if isinstance(full_results[0], list) else str(full_results[0])
        except Exception:
            pass

        openness = get_viseme_openness(final)
        roundness = get_viseme_roundness(final)
        weight = get_duration_weight(final)

        # 闭口辅音：极低开口度，但保持韵母圆展度
        if is_closed_initial(pinyin):
            openness = 0.08
            weight *= 0.65

        frame_specs.append({
            "char": char,
            "openness": openness,
            "roundness": roundness,
            "weight": weight,
            "is_punct": False,
        })

    # ── 按权重分配时长 ──
    total_weight = sum(f["weight"] for f in frame_specs)
    if total_weight <= 0:
        total_weight = len(frame_specs)

    current_ms = 0
    timeline: list[dict] = []
    for spec in frame_specs:
        char_duration = max(round(duration_ms * spec["weight"] / total_weight), 1)
        timeline.append({
            "start": current_ms,
            "end": current_ms + char_duration,
            "value": round(spec["openness"], 3),
            "form": round(spec["roundness"], 3),
            "char": spec["char"],
        })
        current_ms += char_duration

    # ── 合并相邻相同开口度+圆展度的帧 ──
    if timeline:
        timeline[0]["start"] = 0
        timeline[-1]["end"] = int(duration_ms)

    merged = _merge_similar_frames(timeline)

    # ── 帧间缓动：在每个帧末尾追加一个过渡帧 ──
    eased = _add_easing(merged)
    if eased:
        eased[0]["start"] = 0
        eased[-1]["end"] = int(duration_ms)
    return eased


def _merge_similar_frames(frames: list[dict]) -> list[dict]:
    if len(frames) <= 1:
        return frames

    merged = [frames[0]]
    for frame in frames[1:]:
        prev = merged[-1]
        diff_open = abs(frame["value"] - prev["value"])
        diff_form = abs(frame["form"] - prev["form"])
        if diff_open < 0.06 and diff_form < 0.10:
            # 取加权平均
            prev_dur = prev["end"] - prev["start"]
            cur_dur = frame["end"] - frame["start"]
            total = prev_dur + cur_dur
            if total > 0:
                prev["value"] = round((prev["value"] * prev_dur + frame["value"] * cur_dur) / total, 3)
                prev["form"] = round((prev["form"] * prev_dur + frame["form"] * cur_dur) / total, 3)
            prev["end"] = frame["end"]
        else:
            merged.append(frame)
    return merged


def _add_easing(frames: list[dict]) -> list[dict]:
    """帧间线性缓动 — 每帧取后 1/4 作为过渡区。"""
    result: list[dict] = []
    for i, frame in enumerate(frames):
        duration = frame["end"] - frame["start"]
        if i < len(frames) - 1 and duration > 8:
            nxt = frames[i + 1]
            transition_point = frame["start"] + max(round(duration * 0.75), duration - 3)
            result.append({
                "start": frame["start"],
                "end": transition_point,
                "value": frame["value"],
                "form": frame["form"],
            })
            result.append({
                "start": transition_point,
                "end": frame["end"],
                "value": round((frame["value"] + nxt["value"]) / 2, 3),
                "form": round((frame["form"] + nxt["form"]) / 2, 3),
            })
        else:
            result.append(frame)
    return result


def build_viseme_timeline_fallback(text: str, duration_ms: int) -> list[dict]:
    """pypinyin 不可用时的降级方案——改进版原算法。

    比原来的 random cycle 好：区分元音/辅音，用更自然的开口模式。
    """
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return []

    punctuation = set("，。！？；：、,.!?;:""''（）()【】[]{}《》<>…—")
    # 高开口元音偏旁（粗略启发式）
    open_vowels = set("阿啊呀鸭亚雅丫崖涯衙讶压压丫一以意义易已已忆亿役疫益翼亦奕译抑溢")

    frame_duration = max(duration_ms / len(chars), 1)
    # 更自然的口型序列：大开 → 收 → 微开 → 收 → 循环
    natural_pattern = (0.72, 0.38, 0.55, 0.22, 0.65, 0.35, 0.50, 0.15)
    timeline = []
    pattern_idx = 0
    for char in chars:
        start = round(len(timeline) * frame_duration)
        dur = round(frame_duration)
        if char in punctuation:
            value = 0.0
            dur = round(frame_duration * 0.5)
        else:
            value = natural_pattern[pattern_idx % len(natural_pattern)]
            pattern_idx += 1

        end = start + dur
        timeline.append({"start": start, "end": end, "value": round(value, 3), "form": 0.15})
    # 重新对齐 end
    for frame in timeline:
        frame["end"] = min(frame["end"], int(duration_ms))
    if timeline:
        timeline[0]["start"] = 0
        timeline[-1]["end"] = int(duration_ms)
    return timeline
