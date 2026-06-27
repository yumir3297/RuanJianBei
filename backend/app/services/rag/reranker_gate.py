from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.base import RetrievalScope


@dataclass(frozen=True, slots=True)
class RerankerGateDecision:
    should_rerank: bool
    reason: str


class RerankerGate:
    def decide(
        self,
        *,
        scope: RetrievalScope | None,
        candidate_count: int,
        top_k: int,
    ) -> RerankerGateDecision:
        if candidate_count <= 1:
            return RerankerGateDecision(False, "single_candidate")
        if (
            scope is not None
            and scope.source_entry_id is not None
            and candidate_count <= max(top_k, 1)
        ):
            return RerankerGateDecision(False, "exact_scope_within_top_k")
        return RerankerGateDecision(True, "cross_scope_or_ambiguous")
