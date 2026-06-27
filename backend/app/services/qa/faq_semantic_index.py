from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from time import perf_counter
from typing import TYPE_CHECKING, Sequence

from app.services.rag.embedder import BaseEmbedder

if TYPE_CHECKING:
    from app.services.qa.faq_matcher import FAQEntry


@dataclass(frozen=True, slots=True)
class FAQSemanticMatch:
    entry: FAQEntry
    alias: str
    score: float


class FAQSemanticIndex:
    def __init__(self, embedder: BaseEmbedder, threshold: float) -> None:
        self.embedder = embedder
        self.threshold = threshold
        self.alias_count = 0
        self.entry_count = 0
        self.last_build_ms = 0.0
        self._records: list[tuple[FAQEntry, str, list[float]]] = []

    @property
    def model_name(self) -> str:
        return self.embedder.model_name

    def clear(self) -> None:
        self.alias_count = 0
        self.entry_count = 0
        self.last_build_ms = 0.0
        self._records.clear()

    def build(self, entries: Sequence[FAQEntry]) -> float:
        started_at = perf_counter()
        pairs = [(entry, alias) for entry in entries for alias in entry.aliases if alias.strip()]
        vectors = self.embedder.embed_texts([alias for _, alias in pairs])
        if len(vectors) != len(pairs):
            raise RuntimeError("FAQ semantic embedding count does not match alias count.")

        self._records = [
            (entry, alias, [float(value) for value in vector])
            for (entry, alias), vector in zip(pairs, vectors, strict=True)
        ]
        self.alias_count = len(self._records)
        self.entry_count = len(entries)
        self.last_build_ms = (perf_counter() - started_at) * 1000
        return self.last_build_ms

    def match(
        self,
        query: str,
        threshold: float | None = None,
        allowed_entry_ids: frozenset[str] | None = None,
    ) -> FAQSemanticMatch | None:
        if not query.strip() or not self._records:
            return None

        query_vector = self.embedder.embed(query)
        best: FAQSemanticMatch | None = None
        for entry, alias, alias_vector in self._records:
            if allowed_entry_ids is not None and entry.id not in allowed_entry_ids:
                continue
            score = self._cosine_similarity(query_vector, alias_vector)
            if best is None or score > best.score:
                best = FAQSemanticMatch(entry=entry, alias=alias, score=score)

        minimum = self.threshold if threshold is None else threshold
        return best if best is not None and best.score >= minimum else None

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right) or not left:
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)
