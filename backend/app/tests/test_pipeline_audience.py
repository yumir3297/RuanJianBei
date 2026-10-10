from app.schemas.chat import ChatRequest
from app.schemas.selection import SelectionContext
from app.services.qa.pipeline import _resolve_narration_audience


def test_explicit_audience_wins():
    request = ChatRequest(query="大佛多高", session_id="s1", audience="expert")
    assert _resolve_narration_audience(request) == "expert"


def test_defaults_to_adult_without_signal():
    request = ChatRequest(query="大佛多高", session_id="s1")
    assert _resolve_narration_audience(request) == "adult"


def test_family_audience_type_maps_to_child():
    request = ChatRequest(
        query="大佛多高",
        session_id="s1",
        selection=SelectionContext(audience_type="family"),
    )
    assert _resolve_narration_audience(request) == "child"


def test_culture_audience_type_does_not_become_expert():
    """culture 只是路线画像，不应擅自升级为专家讲解。"""
    request = ChatRequest(
        query="大佛多高",
        session_id="s1",
        selection=SelectionContext(audience_type="culture"),
    )
    assert _resolve_narration_audience(request) == "adult"


def test_chat_request_accepts_visitor_id():
    request = ChatRequest(query="大佛多高", session_id="s1", visitor_id="visitor-abc")
    assert request.visitor_id == "visitor-abc"

    assert ChatRequest(query="大佛多高", session_id="s1").visitor_id is None
