from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from app.services.qa.evidence_retrieval import retrieve_evidence
from app.services.qa.stream_events import StreamEvent
from app.services.rag.base import BaseRAGService, RetrievedDocument, RetrievalScope


@dataclass(frozen=True)
class StreamEvidenceOutcome:
    documents: list[RetrievedDocument]
    sources: list[dict]
    error_event: StreamEvent | None = None


class StreamEvidenceRun:
    """Own one request's FAQ/RAG evidence selection and SSE source events."""

    def __init__(
        self,
        *,
        rag_service: BaseRAGService,
        query: str,
        normalized_query: str,
        scope: RetrievalScope | None,
        faq_documents: list[RetrievedDocument] | None,
        faq_sources: list[dict],
        epoch_is_current: Callable[[], Awaitable[bool]],
    ) -> None:
        self.rag_service = rag_service
        self.query = query
        self.normalized_query = normalized_query
        self.scope = scope
        self.faq_documents = faq_documents
        self.faq_sources = faq_sources
        self.epoch_is_current = epoch_is_current
        self.outcome: StreamEvidenceOutcome | None = None

    async def events(self) -> AsyncIterator[StreamEvent]:
        if self.faq_documents is not None:
            yield StreamEvent(type="status", data={"text": "正在按你的讲解方式改写..."})
            documents = self.faq_documents
            sources = self.faq_sources
            if not await self.epoch_is_current():
                self.outcome = StreamEvidenceOutcome(documents=[], sources=[], error_event=self._stale_event())
                yield self.outcome.error_event
                return
        else:
            yield StreamEvent(type="status", data={"text": "正在检索景区知识..."})
            evidence = await retrieve_evidence(
                self.rag_service,
                query=self.query,
                normalized_query=self.normalized_query,
                scope=self.scope,
            )
            documents = evidence.documents
            sources = evidence.sources
            if not await self.epoch_is_current():
                self.outcome = StreamEvidenceOutcome(documents=[], sources=[], error_event=self._stale_event())
                yield self.outcome.error_event
                return

        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})

        # Keep the post-source fence as a separate check: the visibility epoch
        # may change while the source event is being yielded to the SSE client.
        if not await self.epoch_is_current():
            self.outcome = StreamEvidenceOutcome(documents=[], sources=[], error_event=self._stale_event())
            yield self.outcome.error_event
            return

        self.outcome = StreamEvidenceOutcome(documents=documents, sources=sources)

    @staticmethod
    def _stale_event() -> StreamEvent:
        return StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
