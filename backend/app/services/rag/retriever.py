from __future__ import annotations

from collections import Counter

from app.repositories.knowledge import KnowledgeRepository
from app.services.rag.base import BaseRAGService, RetrievalScope, RetrievedDocument
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker


class RepositoryBackedRAGService(BaseRAGService):
    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        query_rewriter: QueryRewriter,
        reranker: Reranker,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.query_rewriter = query_rewriter
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        normalized_query: str | None = None,
        top_k: int = 5,
        scope: RetrievalScope | None = None,
    ) -> list[RetrievedDocument]:
        normalized = normalized_query or self.query_rewriter.rewrite(query)
        candidates = self.knowledge_repository.search(
            normalized,
            limit=max(top_k * 4, 10),
            knowledge_id=scope.source_entry_id if scope else None,
            category=scope.category if scope else None,
        )

        documents: list[RetrievedDocument] = []
        query_tokens = Counter(token for token in normalized.split(" ") if token)

        for entry in candidates:
            haystack = f"{entry.title} {entry.content} {entry.aliases}"
            score = sum(haystack.count(token) for token in query_tokens)
            documents.append(
                RetrievedDocument(
                    title=entry.title,
                    content=entry.content,
                    snippet=entry.content[:160],
                    source=entry.source,
                    score=float(score),
                )
            )

        ranked = self.reranker.rerank(query, documents, top_k=top_k)
        return [item.document for item in ranked]
