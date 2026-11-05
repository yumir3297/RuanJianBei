from __future__ import annotations

from types import SimpleNamespace

from app.schemas.chat import ChatRequest, ConversationContext, VisionContext
from app.schemas.selection import SelectionContext
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.request_query_context import resolve_request_query_context
from app.services.rag.base import RetrievalScope


def _resolved(*, active_subject=None, selection=None):
    return ResolvedInteraction(
        selection=selection or SelectionContext(),
        scope=RetrievalScope(source_entry_id=12) if active_subject else None,
        resolution_source="history" if active_subject else "default",
        active_subject=active_subject,
    )


def test_vision_hint_enriches_retrieval_but_not_intent_or_inherited_context() -> None:
    class RecordingRewriter:
        def __init__(self):
            self.call = None

        def rewrite(self, query, context):
            self.call = (query, context)
            return f"normalized:{query}"

    class RecordingIntentRouter:
        def __init__(self):
            self.call = None

        def detect(self, query, selection):
            self.call = (query, selection)
            return SimpleNamespace(intent="static_qa", confidence=0.55, matched_keywords=())

    context = ConversationContext(last_subject="旧景点", history_summary="之前的对话")
    selection = SelectionContext(mode="attraction", attraction_id=12)
    request = ChatRequest(query="这是什么建筑", session_id="query-context", context=context, selection=selection)
    vision = VisionContext(retrieval_query="大佛莲花座造型")
    rewriter = RecordingRewriter()
    router = RecordingIntentRouter()

    resolved = resolve_request_query_context(
        request,
        _resolved(selection=selection),
        vision=vision,
        query_rewriter=rewriter,
        intent_router=router,
    )

    assert resolved.retrieval_query == "这是什么建筑\n大佛莲花座造型"
    assert resolved.normalized_query == "normalized:这是什么建筑\n大佛莲花座造型"
    assert rewriter.call == (resolved.retrieval_query, None)
    assert router.call == ("这是什么建筑", selection)
    assert resolved.intent_decision.intent == "static_qa"


def test_resolved_active_subject_replaces_context_subject_and_keeps_history_summary() -> None:
    context = ConversationContext(last_subject="之前景点", history_summary="游客问过交通")
    request = ChatRequest(query="还有什么看点", session_id="query-context-history", context=context)
    rewriter = SimpleNamespace(rewrite=lambda query, rewrite_context: (query, rewrite_context))
    router = SimpleNamespace(detect=lambda query, selection: SimpleNamespace(
        intent="static_qa", confidence=0.55, matched_keywords=(),
    ))

    resolved = resolve_request_query_context(
        request,
        _resolved(active_subject="灵山大佛"),
        vision=None,
        query_rewriter=rewriter,
        intent_router=router,
    )

    normalized_query, rewrite_context = resolved.normalized_query
    assert resolved.retrieval_query == "还有什么看点"
    assert normalized_query == "还有什么看点"
    assert rewrite_context == ConversationContext(
        last_subject="灵山大佛",
        history_summary="游客问过交通",
    )


def test_unscoped_text_request_reuses_conversation_context_object() -> None:
    context = ConversationContext(last_subject="灵山大佛", history_summary="文化讲解")
    request = ChatRequest(query="请展开讲讲", session_id="query-context-same", context=context)
    captured = {}

    def rewrite(query, rewrite_context):
        captured["call"] = (query, rewrite_context)
        return "normalized query"

    resolved = resolve_request_query_context(
        request,
        _resolved(),
        vision=None,
        query_rewriter=SimpleNamespace(rewrite=rewrite),
        intent_router=SimpleNamespace(detect=lambda *_: SimpleNamespace(
            intent="static_qa", confidence=0.55, matched_keywords=(),
        )),
    )

    assert resolved.retrieval_query == request.query
    assert captured["call"] == (request.query, context)
