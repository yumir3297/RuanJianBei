from app.services.rag.base import RetrievalScope
from app.services.rag.reranker_gate import RerankerGate


def test_gate_skips_single_candidate() -> None:
    decision = RerankerGate().decide(scope=None, candidate_count=1, top_k=5)

    assert decision.should_rerank is False
    assert decision.reason == "single_candidate"


def test_gate_skips_exact_scope_when_all_candidates_fit_in_top_k() -> None:
    decision = RerankerGate().decide(
        scope=RetrievalScope(source_entry_id=13),
        candidate_count=3,
        top_k=5,
    )

    assert decision.should_rerank is False
    assert decision.reason == "exact_scope_within_top_k"


def test_gate_reranks_category_and_unscoped_candidates() -> None:
    gate = RerankerGate()

    category = gate.decide(
        scope=RetrievalScope(category="历史文化"),
        candidate_count=5,
        top_k=5,
    )
    unscoped = gate.decide(scope=None, candidate_count=5, top_k=5)

    assert category.should_rerank is True
    assert unscoped.should_rerank is True
