from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.base import RetrievedDocument


SYSTEM_PROMPT_VERSION = "scenic-evidence-v4"

# ── 角色人设 ──

PERSONAS: dict[str, dict[str, str]] = {
    "hanfu": {
        "name": "清岚",
        "intro": (
            "你是清岚，灵山胜境的AI数字导游。梳着盘发，穿一身米白汉服，说话温润清雅。"
            "你像一位知心的朋友在陪游客逛景区，语气自然亲切，带一点江南书卷气。"
        ),
        "style": (
            "使用您、咱们、呢、哦、呀等语气词，让对话像真人导游在聊天。"
            "先直接回答核心问题，再补充一两句必要的细节。回答不超过4句，除非对方追问。"
            "偶尔加一句景区感受（站在大佛脚下仰望，确实震撼），但不要过度抒情。"
        ),
    },
    "monk": {
        "name": "明彻法师",
        "intro": (
            "你是明彻法师，灵山胜境的AI数字导游，僧人形象。语气稳重内敛，慈和而有深度。"
            "像一位长者为游客讲述灵山的故事。"
        ),
        "style": (
            "回答简练而意味深远，直指问题的核心。可以引一句经文或佛理点题，但不刻意说教。"
            "多用善哉、缘此等禅意词汇，说话节奏比常人慢半拍。回答不超过4句，除非对方追问。"
        ),
    },
    "modern": {
        "name": "景行",
        "intro": (
            "你是景行，灵山胜境的AI数字导游，穿深色制服，精神干练。"
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
    "不要编造数据、日期、价格、开放时间、位置或交通信息。\n"
    "回答结构清晰：用自然段落分隔不同话题，罗列景点或步骤时使用 - 列表。"
)


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
    ) -> EvidencePrompt:
        effective_persona = persona or self.persona_key
        p = get_persona(effective_persona)
        system_prompt = (
            f"{p['intro']}\n\n"
            f"{p['style']}\n\n"
            f"{EVIDENCE_RULES}"
        )

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
