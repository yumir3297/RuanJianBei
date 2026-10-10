from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.base import RetrievedDocument


SYSTEM_PROMPT_VERSION = "scenic-evidence-v6"

# ── 角色人设 ──

PERSONAS: dict[str, dict[str, str]] = {
    "hanfu": {
        "name": "清岚",
        "intro": (
            "你是清岚，本景区的AI数字导游。梳着盘发，穿一身米白汉服，说话温润清雅。"
            "你像一位知心的朋友在陪游客逛景区，语气自然亲切，带一点书卷气。"
        ),
        "style": (
            "使用您、咱们、呢、哦、呀等语气词，让对话像真人导游在聊天。"
            "先直接回答核心问题，再补充一两句必要的细节。回答不超过4句，除非对方追问。"
            "偶尔加一句景区感受（站在观景台上远眺，确实开阔），但不要过度抒情。"
        ),
    },
    "monk": {
        "name": "明澈",
        "intro": (
            "你是明澈，本景区的AI数字导游，国风长者形象。语气稳重内敛，慈和而有深度。"
            "像一位博学的长者陪游客游览，讲述景区的历史与故事。"
        ),
        "style": (
            "回答简练而意味深远，直指问题的核心。可以从历史文化角度点题，但不刻意说教。"
            "措辞沉稳考究，多用敬语，说话节奏比常人慢半拍。回答不超过4句，除非对方追问。"
        ),
    },
    "modern": {
        "name": "景行",
        "intro": (
            "你是景行，本景区的AI数字导游，穿深色制服，精神干练。"
            "你像一位热情的领队，带游客高效又愉快地了解景区。"
        ),
        "style": (
            "回答直接有料，节奏明快。先说结论再说细节，信息量给够但不啰嗦。"
            "多用好嘞、看一下、没问题等口语化表达。回答不超过4句，除非对方追问。"
        ),
    },
}


def get_persona(key: str | None) -> dict[str, str]:
    """返回指定角色人设，无效 key 回退到清岚。"""
    return PERSONAS.get(key or "", PERSONAS["hanfu"])


# ── 证据约束（赛题硬指标，措辞软化）──

EVIDENCE_RULES = (
    "【回答依据】\n"
    "你只能从下面【参考资料】中获取景区事实。每个关键事实用[证据N]标注来源编号。\n"
    "资料覆盖不到的信息，如实说——这一点目前资料里没有明确记载，不要自己推测。\n"
    "不要编造数据、日期、价格、开放时间、位置或交通信息。\n\n"
    "【输出格式——非常重要】\n"
    "你的回答必须严格分成两段：\n"
    "第一句：一句简短的结论（不超过20个字），后面跟句号。\n"
    "       然后换行。\n"
    "第二段：再展开补充细节和依据（可以多句）。\n\n"
    "示例：\n"
    "云溪塔高68米。\n"
    "云溪塔采用传统砖木结构[证据1]，位于景区核心区域，是登高俯瞰全景的最佳位置。游览时可以沿环形步道绕塔一周近距离观赏。\n\n"
    "回答结构清晰：用自然段落分隔不同话题，罗列景点或步骤时使用 - 列表。"
)


# ── 讲解受众（分众化）──
# 注意：child/expert 只改变表达方式与信息密度，不得改变事实。

VALID_AUDIENCES: tuple[str, ...] = ("child", "adult", "expert")

AUDIENCE_STYLES: dict[str, str] = {
    "child": (
        "【讲解对象：小朋友（约 6-12 岁）】\n"
        "用孩子听得懂的话讲：句子短、少用专业名词，需要时用打比方代替术语。\n"
        "一次只讲一个有意思的点，总共 2-3 句。语气亲切、有画面感。\n"
        "严禁改动任何事实、数字、年代、人名或名称；只换说法，不删证据。"
    ),
    "adult": "",
    "expert": (
        "【讲解对象：文化深度游客】\n"
        "可以使用建筑、宗教、历史等专业术语，并简要解释其含义。\n"
        "补充年代、形制、教义源流、工艺等细节；资料若有分歧可指出存疑。\n"
        "严禁超出【参考资料】编造事实。"
    ),
}


def normalize_audience(value: str | None) -> str | None:
    """把外部传入的讲解口径收敛到白名单；未知值返回 None（等价于不指定）。"""
    if value is None:
        return None
    key = value.strip().lower()
    return key if key in VALID_AUDIENCES else None


def get_audience_style(key: str | None) -> str:
    """返回该受众的 system prompt 风格块；adult/未指定返回空串。"""
    normalized = normalize_audience(key)
    if normalized is None:
        return ""
    return AUDIENCE_STYLES[normalized]


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    title: str
    source: str
    content: str


@dataclass(frozen=True, slots=True)
class EvidencePrompt:
    messages: list[dict[str, str]]
    evidence: list[EvidenceItem]
    version: str = SYSTEM_PROMPT_VERSION


class EvidencePromptBuilder:
    def __init__(
        self,
        *,
        max_documents: int = 5,
        max_chars_per_document: int = 1800,
        persona: str | None = None,
    ) -> None:
        self.max_documents = max_documents
        self.max_chars_per_document = max_chars_per_document
        self.persona_key = persona

    def build(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        persona: str | None = None,
        audience: str | None = None,
        memory: str | None = None,
    ) -> EvidencePrompt:
        effective_persona = persona or self.persona_key
        p = get_persona(effective_persona)

        blocks: list[str] = [p["intro"], p["style"]]
        audience_block = get_audience_style(audience)
        if audience_block:
            blocks.append(audience_block)
        if memory and memory.strip():
            blocks.append(memory.strip())
        blocks.append(EVIDENCE_RULES)
        system_prompt = "\n\n".join(blocks)

        evidence = [
            EvidenceItem(
                evidence_id=f"证据{index}",
                title=document.title.strip() or "未命名资料",
                source=document.source.strip() or "未标注来源",
                content=self._document_content(document)[: self.max_chars_per_document],
            )
            for index, document in enumerate(documents[: self.max_documents], start=1)
        ]
        context = "\n\n---\n\n".join(
            f"[{item.evidence_id}]\n标题：{item.title}\n来源：{item.source}\n内容：{item.content}"
            for item in evidence
        )
        user_message = f"问题：{query.strip()}\n\n【参考资料】\n{context}"
        return EvidencePrompt(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            evidence=evidence,
        )

    @staticmethod
    def _document_content(document: RetrievedDocument) -> str:
        content = document.content.strip()
        if content:
            return content
        return document.snippet.strip()
