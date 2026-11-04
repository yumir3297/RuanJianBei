from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.base import BaseRAGService, RetrievedDocument, RetrievalScope


@dataclass(slots=True)
class RetrievedEvidence:
    documents: list[RetrievedDocument]
    sources: list[dict]


async def retrieve_evidence(
    rag_service: BaseRAGService,
    *,
    query: str,
    normalized_query: str,
    scope: RetrievalScope | None,
) -> RetrievedEvidence:
    documents = await rag_service.retrieve(
        query,
        normalized_query=normalized_query,
        scope=scope,
    )
    sources = [
        {
            "evidence_id": f"证据{index}",
            "title": document.title,
            "snippet": document.snippet,
            "source": document.source,
            "score": document.score,
            "entry_id": document.entry_id,
            "revision_id": document.revision_id,
            "chunk_id": document.chunk_id,
        }
        for index, document in enumerate(documents, start=1)
    ]
    return RetrievedEvidence(documents=documents, sources=sources)
