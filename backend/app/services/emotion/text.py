from __future__ import annotations

import re

from app.services.emotion.models import EmotionLabel, EmotionSignal


_RAW_PATTERNS: dict[EmotionLabel, tuple[str, ...]] = {
    EmotionLabel.URGENT: (
        r"(孩子|老人|家人).{0,6}(不见|走失|找不到)",
        r"(受伤|流血|晕倒|昏倒|呼吸困难|胸痛|中暑)",
        r"(着火|火灾|救命|报警|被困|踩踏)",
    ),
    EmotionLabel.ANXIOUS: (
        r"(迷路|走丢|找不到出口|回不去|赶不上)",
        r"(不舒服|头晕|害怕|担心|着急|焦虑)",
        r"(东西|手机|钱包|证件).{0,5}(丢了|不见了)",
    ),
    EmotionLabel.DISSATISFIED: (
        r"(太差|很差|糟糕|坑人|失望|不满意|不是很满意)",
        r"(回答|介绍|路线|推荐).{0,6}(不准|错误|有问题|没用)",
        r"(投诉|退票|排队太久|等了半天|态度差|体验不好)",
    ),
    EmotionLabel.CONFUSED: (
        r"(没听懂|听不懂|不明白|看不懂|什么意思)",
        r"(怎么走|往哪走|找不到路|路线看不懂)",
        r"(再说一遍|简单一点|讲清楚|能不能解释)",
    ),
    EmotionLabel.POSITIVE: (
        r"(太漂亮|真漂亮|好美|震撼|壮观|好棒|太棒)",
        r"(喜欢|满意|开心|值得|有意思)",
        r"(谢谢|感谢|辛苦了|讲得很好)",
    ),
}


_CP1252_REVERSE = {
    0x20AC: 0x80, 0x201A: 0x82, 0x0192: 0x83, 0x201E: 0x84,
    0x2026: 0x85, 0x2020: 0x86, 0x2021: 0x87, 0x02C6: 0x88,
    0x2030: 0x89, 0x0160: 0x8A, 0x2039: 0x8B, 0x0152: 0x8C,
    0x017D: 0x8E, 0x2018: 0x91, 0x2019: 0x92, 0x201C: 0x93,
    0x201D: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97,
    0x02DC: 0x98, 0x2122: 0x99, 0x0161: 0x9A, 0x203A: 0x9B,
    0x0153: 0x9C, 0x017E: 0x9E, 0x0178: 0x9F,
}


def _decode_mojibake(value: str) -> str:
    """Recover UTF-8 text decoded through a Windows single-byte code page."""
    raw = bytearray()
    for character in value:
        codepoint = ord(character)
        if codepoint <= 0xFF:
            raw.append(codepoint)
        elif codepoint in _CP1252_REVERSE:
            raw.append(_CP1252_REVERSE[codepoint])
        else:
            return value
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return value


_PATTERNS = {
    label: tuple(_decode_mojibake(pattern) for pattern in patterns)
    for label, patterns in _RAW_PATTERNS.items()
}


class TextEmotionAnalyzer:
    """Low-latency scenic-domain semantic emotion baseline with safety overrides."""

    def analyze(self, text: str) -> EmotionSignal:
        normalized = re.sub(r"\s+", "", text or "")
        if not normalized:
            return EmotionSignal(
                label=EmotionLabel.NEUTRAL,
                confidence=0.0,
                intensity=0.0,
                source="text_rules",
                available=False,
            )

        for label in (
            EmotionLabel.URGENT,
            EmotionLabel.ANXIOUS,
            EmotionLabel.DISSATISFIED,
            EmotionLabel.CONFUSED,
            EmotionLabel.POSITIVE,
        ):
            evidence = tuple(
                match.group(0)
                for pattern in _PATTERNS[label]
                if (match := re.search(pattern, normalized, flags=re.IGNORECASE))
            )
            if evidence:
                base_confidence = {
                    EmotionLabel.URGENT: 0.98,
                    EmotionLabel.ANXIOUS: 0.88,
                    EmotionLabel.DISSATISFIED: 0.87,
                    EmotionLabel.CONFUSED: 0.84,
                    EmotionLabel.POSITIVE: 0.83,
                }[label]
                intensity = min(0.55 + 0.16 * len(evidence), 1.0)
                if any(mark in text for mark in ("！", "!", "！？", "??")):
                    intensity = min(intensity + 0.12, 1.0)
                return EmotionSignal(
                    label=label,
                    confidence=min(base_confidence + 0.03 * (len(evidence) - 1), 0.99),
                    intensity=round(intensity, 3),
                    source="text_rules",
                    evidence=evidence,
                )

        return EmotionSignal(
            label=EmotionLabel.NEUTRAL,
            confidence=0.72,
            intensity=0.2,
            source="text_rules",
        )
