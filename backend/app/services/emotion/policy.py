from __future__ import annotations

from dataclasses import dataclass

from app.services.emotion.models import EmotionLabel, FusedEmotion


@dataclass(frozen=True, slots=True)
class EmotionResponsePolicy:
    label: EmotionLabel
    avatar_emotion: str
    answer_prefix: str
    prompt_guidance: str


_POLICIES = {
    EmotionLabel.POSITIVE: EmotionResponsePolicy(
        EmotionLabel.POSITIVE,
        "happy",
        "",
        "语气可以更亲切、轻快，但仍要准确简洁。",
    ),
    EmotionLabel.CONFUSED: EmotionResponsePolicy(
        EmotionLabel.CONFUSED,
        "relaxed",
        "没关系，我换一种更简单的说法。",
        "先给直接结论，再分步骤说明；少用术语，并明确下一步怎么做。",
    ),
    EmotionLabel.DISSATISFIED: EmotionResponsePolicy(
        EmotionLabel.DISSATISFIED,
        "apology",
        "抱歉给您带来了不好的体验。",
        "先简短致歉并承认问题，再给可执行的解决办法；不要争辩或过度解释。",
    ),
    EmotionLabel.ANXIOUS: EmotionResponsePolicy(
        EmotionLabel.ANXIOUS,
        "sad",
        "先别着急，我来帮您一步一步处理。",
        "语气沉稳，优先给当前最重要的一步，再给后续步骤；避免堆砌信息。",
    ),
    EmotionLabel.URGENT: EmotionResponsePolicy(
        EmotionLabel.URGENT,
        "apology",
        "请先确保人身安全。",
        "这是紧急情况：把立即行动放在第一句，建议联系现场工作人员或公共紧急服务；不得编造电话、位置或处置承诺。",
    ),
    EmotionLabel.NEUTRAL: EmotionResponsePolicy(
        EmotionLabel.NEUTRAL,
        "speaking",
        "",
        "保持自然、清晰、友好的导游表达。",
    ),
}


def response_policy_for(emotion: FusedEmotion) -> EmotionResponsePolicy:
    return _POLICIES[emotion.label]


def apply_answer_prefix(answer: str, policy: EmotionResponsePolicy) -> str:
    clean_answer = answer.strip()
    if not policy.answer_prefix or clean_answer.startswith(policy.answer_prefix):
        return clean_answer
    return f"{policy.answer_prefix}\n\n{clean_answer}"
