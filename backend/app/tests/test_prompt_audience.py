import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.services.llm.prompt_builder import (
    SYSTEM_PROMPT_VERSION,
    EvidencePromptBuilder,
    get_audience_style,
    normalize_audience,
)
from app.services.rag.base import RetrievedDocument


def _doc():
    return RetrievedDocument(
        title="灵山大佛",
        content="灵山大佛通高88米，1997年落成。",
        snippet="灵山大佛通高88米。",
        source="灵山胜境官方资料",
        score=0.9,
    )


def test_version_bumped_past_v5():
    assert SYSTEM_PROMPT_VERSION != "scenic-evidence-v5"


def test_normalize_audience_accepts_known_and_rejects_unknown():
    assert normalize_audience("child") == "child"
    assert normalize_audience(" Expert ") == "expert"
    assert normalize_audience("adult") == "adult"
    assert normalize_audience(None) is None
    assert normalize_audience("toddler") is None


def test_audience_style_is_empty_for_adult_and_none():
    assert get_audience_style("adult") == ""
    assert get_audience_style(None) == ""


def test_child_style_forbids_fact_changes():
    style = get_audience_style("child")
    assert "小朋友" in style
    assert "数字" in style and "年" in style
    assert "严禁" in style


def test_build_injects_audience_block_into_system_prompt():
    builder = EvidencePromptBuilder()
    prompt = builder.build("大佛多高", [_doc()], audience="child")
    system = prompt.messages[0]["content"]
    assert "小朋友" in system
    # 受众块必须出现在证据规则之前
    assert system.index("小朋友") < system.index("【回答依据】")


def test_build_without_audience_keeps_system_prompt_free_of_audience_blocks():
    builder = EvidencePromptBuilder()
    prompt = builder.build("大佛多高", [_doc()])
    system = prompt.messages[0]["content"]
    assert "小朋友" not in system
    assert "文化深度游客" not in system


def test_expert_style_allows_terminology_but_forbids_fabrication():
    style = get_audience_style("expert")
    assert "专业术语" in style
    assert "严禁" in style


def test_chat_request_accepts_audience_and_rejects_unknown():
    ok = ChatRequest(query="大佛多高", session_id="s1", audience="child")
    assert ok.audience == "child"

    default = ChatRequest(query="大佛多高", session_id="s1")
    assert default.audience is None

    with pytest.raises(ValidationError):
        ChatRequest(query="大佛多高", session_id="s1", audience="toddler")
