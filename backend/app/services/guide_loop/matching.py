from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from app.schemas.guide_loop import MatchDecision, QuestionContext
from app.services.rag.embedder import BaseEmbedder


_TIME_TERMS = ("今天", "明天", "后天", "现在", "下一场", "几点", "什么时候", "日期", "演出", "活动", "开放")


def _time_sensitive(*contexts: QuestionContext) -> bool:
    return any(term in ctx.text for ctx in contexts for term in _TIME_TERMS)


def match_pair(
    left: QuestionContext,
    right: QuestionContext,
    score: float,
    threshold: float,
) -> MatchDecision:
    """Apply scope and time guards before semantic similarity can merge a pair."""
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("score must be a finite value between 0 and 1")
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be a finite value between 0 and 1")

    if left.poi_id and right.poi_id and left.poi_id != right.poi_id:
        return MatchDecision(decision="distinct", reason_code="poi_conflict", score=score)
    if left.target_id and right.target_id and left.target_id != right.target_id:
        return MatchDecision(decision="distinct", reason_code="target_conflict", score=score)
    if _time_sensitive(left, right):
        if left.queried_date and right.queried_date and left.queried_date != right.queried_date:
            return MatchDecision(decision="distinct", reason_code="date_conflict", score=score)
        if not left.queried_date or not right.queried_date:
            return MatchDecision(decision="clarify", reason_code="missing_date", score=score)
    if score < threshold:
        return MatchDecision(decision="distinct", reason_code="below_similarity_threshold", score=score)
    if not left.poi_id or not right.poi_id:
        return MatchDecision(decision="clarify", reason_code="unknown_scope", score=score)
    if not left.target_id or not right.target_id:
        return MatchDecision(decision="clarify", reason_code="missing_target", score=score)
    return MatchDecision(decision="reuse", reason_code="same_scope_high_similarity", score=score)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def rank_candidates(
    question: str,
    candidates: Sequence[Mapping[str, Any]],
    embedder: BaseEmbedder,
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return stable top-k semantic candidates; policy decisions remain separate."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if not candidates:
        return []
    texts = [str(candidate.get("text", "")) for candidate in candidates]
    if any(not text.strip() for text in texts):
        raise ValueError("every candidate must have non-empty text")
    vectors = embedder.embed_texts([question, *texts])
    if len(vectors) != len(candidates) + 1:
        raise ValueError("embedder returned an unexpected number of vectors")
    question_vector = vectors[0]
    ranked = []
    for index, (candidate, vector) in enumerate(zip(candidates, vectors[1:])):
        item = dict(candidate)
        item["score"] = _cosine(question_vector, vector)
        ranked.append((item, index))
    ranked.sort(key=lambda pair: (-pair[0]["score"], pair[1]))
    return [item for item, _index in ranked[:top_k]]
