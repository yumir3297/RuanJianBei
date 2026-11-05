from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.schemas.chat import ChatRequest
from app.services.qa.stream_generation_run import StreamGenerationRun
from app.services.rag.base import RetrievedDocument


class StreamAnswerGenerationFactory:
    """Bind request, evidence, and terminal-policy inputs to a generation run."""

    def __init__(
        self,
        *,
        turn_factory,
        llm_provider_name: str,
        emotion_aware_query: Callable[[str], str],
        epoch_is_current: Callable[[], Awaitable[bool]],
    ) -> None:
        self.turn_factory = turn_factory
        self.llm_provider_name = llm_provider_name
        self.emotion_aware_query = emotion_aware_query
        self.epoch_is_current = epoch_is_current

    def build(
        self,
        *,
        request: ChatRequest,
        documents: list[RetrievedDocument],
        audience: str | None,
        memory: str | None,
        confirmed_visual_title: str | None,
        vision_context_present: bool,
        faq_documents_present: bool,
        cache_allowed: bool,
        llm_hit_level: str,
        fallback_hit_level: str,
        faq_answer: str,
        faq_sources: list[dict],
    ) -> StreamGenerationRun:
        return StreamGenerationRun(
            turn_factory=self.turn_factory,
            turn_kwargs={
                "query": request.query,
                "documents": documents,
                "persona": request.persona,
                "audience": audience,
                "memory": memory,
                "confirmed_visual_title": confirmed_visual_title,
                "vision_context_present": vision_context_present,
                "faq_documents_present": faq_documents_present,
                "text_only": request.text_only,
                "epoch_is_current": self.epoch_is_current,
                "emotion_aware_query": self.emotion_aware_query,
            },
            finalization_kwargs={
                "faq_documents_present": faq_documents_present,
                "cache_allowed": cache_allowed,
                "llm_hit_level": llm_hit_level,
                "fallback_hit_level": fallback_hit_level,
                "llm_provider": self.llm_provider_name,
                "faq_answer": faq_answer,
                "persona": request.persona,
                "faq_sources": faq_sources,
            },
        )
