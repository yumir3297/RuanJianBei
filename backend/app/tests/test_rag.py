from app.schemas.chat import ConversationContext
from app.services.rag.query_rewriter import QueryRewriter


def test_query_rewriter_uses_alias_and_context() -> None:
    rewriter = QueryRewriter()

    rewritten = rewriter.rewrite("那个大佛啥时候建的来着", ConversationContext(last_subject="灵山大佛"))

    assert "灵山大佛" in rewritten
    assert "时间" in rewritten

