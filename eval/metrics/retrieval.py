from __future__ import annotations


def recall_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = set(retrieved_ids[:k]) & relevant_ids
    return len(hits) / len(relevant_ids)


def hit_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    return float(bool(set(retrieved_ids[:k]) & relevant_ids))


def reciprocal_rank(relevant_ids: set[str], retrieved_ids: list[str]) -> float:
    if not relevant_ids:
        return 0.0
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
