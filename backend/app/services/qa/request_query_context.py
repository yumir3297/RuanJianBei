from __future__ import annotations

from dataclasses import dataclass

from app.schemas.chat import ChatRequest, ConversationContext, VisionContext
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.intent_router import IntentDecision, IntentRouter
from app.services.rag.query_rewriter import QueryRewriter


@dataclass(frozen=True, slots=True)
class RequestQueryContext:
    retrieval_query: str
    normalized_query: str
    intent_decision: IntentDecision


def resolve_request_query_context(
    request: ChatRequest,
    resolved: ResolvedInteraction,
    *,
    vision: VisionContext | None,
    query_rewriter: QueryRewriter,
    intent_router: IntentRouter,
) -> RequestQueryContext:
    """Build retrieval/rewrite context while keeping intent on the raw query."""
    rewrite_context = None if vision is not None else request.context
    if resolved.active_subject:
        rewrite_context = ConversationContext(
            last_subject=resolved.active_subject,
            history_summary=request.context.history_summary if request.context else None,
        )

    retrieval_query = request.query
    if vision is not None:
        hint = vision.retrieval_query.strip()[:1000]
        if hint and hint not in retrieval_query:
            retrieval_query = f"{retrieval_query}\n{hint}"

    normalized_query = query_rewriter.rewrite(retrieval_query, rewrite_context)
    intent_decision = intent_router.detect(request.query, resolved.selection)
    return RequestQueryContext(
        retrieval_query=retrieval_query,
        normalized_query=normalized_query,
        intent_decision=intent_decision,
    )
