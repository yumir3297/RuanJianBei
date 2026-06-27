from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.services.llm.types import LLMStreamEvent
from app.services.rag.base import RetrievedDocument


class BaseLLMService(ABC):
    @abstractmethod
    async def stream_generate(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        persona: str | None = None,
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        """Yield answer chunks for the current query."""
