from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import aclosing

from app.schemas.chat import ChatRequest
from app.services.emotion import EmotionResponsePolicy
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.qa.answer_styler import no_evidence_reply
from app.services.qa.stream_events import StreamEvent

logger = logging.getLogger(__name__)


class NoEvidenceAnswerHandler:
    """Record an empty RAG result fail-soft, then emit the standard fallback answer."""

    def __init__(self, *, fast_path_answer_factory, blind_spot_tracker=None) -> None:
        self.fast_path_answer_factory = fast_path_answer_factory
        self.blind_spot_tracker = blind_spot_tracker

    async def events(
        self,
        *,
        request: ChatRequest,
        normalized_query: str,
        start: float,
        resolved: ResolvedInteraction,
        response_policy: EmotionResponsePolicy,
        expected_epoch: int | None,
    ) -> AsyncIterator[StreamEvent]:
        if self.blind_spot_tracker is not None:
            try:
                await self.blind_spot_tracker.record(
                    raw_query=request.query,
                    normalized_query=normalized_query,
                    category="rag_no_docs",
                )
                logger.info("Blind spot recorded (RAG no docs)")
            except Exception:
                logger.exception("Knowledge blind spot recording failed")

        async with aclosing(
            self.fast_path_answer_factory.events(
                request=request,
                normalized_query=normalized_query,
                answer=no_evidence_reply(request.persona),
                sources=[],
                hit_level="rag_insufficient",
                start=start,
                resolved=resolved,
                response_policy=response_policy,
                expected_epoch=expected_epoch,
            )
        ) as answer_events:
            async for event in answer_events:
                yield event
