from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


def _dedupe_non_empty(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return tuple(items)


@dataclass(slots=True)
class VisionResult:
    """Vision output is a retrieval hint, not an authoritative scenic fact."""

    scene_summary: str = ""
    detected_text: str = ""
    candidate_attractions: tuple[str, ...] = ()
    visual_tags: tuple[str, ...] = ()
    query_hints: tuple[str, ...] = ()
    confidence: float = 0.0
    provider: str = "stub"
    raw: dict[str, Any] = field(default_factory=dict)

    def retrieval_terms(self) -> tuple[str, ...]:
        return _dedupe_non_empty(
            [
                self.scene_summary,
                self.detected_text,
                *self.candidate_attractions,
                *self.visual_tags,
                *self.query_hints,
            ]
        )

    def as_retrieval_query(self, user_question: str | None = None) -> str:
        terms = list(self.retrieval_terms())
        if user_question:
            terms.insert(0, user_question)
        return "；".join(_dedupe_non_empty(terms))


class BaseVisionService(ABC):
    @abstractmethod
    async def analyze(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionResult:
        """Analyze an image and return retrieval hints for the RAG pipeline."""

    async def aclose(self) -> None:
        """Release provider resources if the implementation owns any."""
