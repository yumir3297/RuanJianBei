from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedDocument:
    title: str
    content: str = ""
    snippet: str = ""
    source: str = ""
    score: float = 0.0


@dataclass(frozen=True, slots=True)
class RetrievalScope:
    source_entry_id: int | None = None
    category: str | None = None

    def is_empty(self) -> bool:
        return self.source_entry_id is None and self.category is None


class BaseRAGService(ABC):
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        normalized_query: str | None = None,
        top_k: int = 5,
        scope: RetrievalScope | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve the most relevant knowledge snippets."""
