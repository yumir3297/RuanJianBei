from __future__ import annotations

import logging
from time import perf_counter

from app.services.rag.base import BaseRAGService, RetrievalScope, RetrievedDocument
from app.services.rag.embedder import BaseEmbedder
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.services.rag.reranker_gate import RerankerGate
from app.services.rag.vector_store import BaseVectorStore

logger = logging.getLogger(__name__)


class VectorBackedRAGService(BaseRAGService):
    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedder: BaseEmbedder,
        query_rewriter: QueryRewriter,
        reranker: Reranker,
        fallback: BaseRAGService | None = None,
        candidate_k: int = 20,
        reranker_gate: RerankerGate | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedder = embedder
        self.query_rewriter = query_rewriter
        self.reranker = reranker
        self.fallback = fallback
        self.candidate_k = max(candidate_k, 1)
        self.reranker_gate = reranker_gate or RerankerGate()
        self.last_mode = "not_run"
        self.last_embedding_ms = 0.0
        self.last_vector_query_ms = 0.0
        self.last_rerank_ms = 0.0
        self.last_reranker_mode = "not_run"

    async def retrieve(
        self,
        query: str,
        normalized_query: str | None = None,
        top_k: int = 5,
        scope: RetrievalScope | None = None,
    ) -> list[RetrievedDocument]:
        self.last_embedding_ms = 0.0
        self.last_vector_query_ms = 0.0
        self.last_rerank_ms = 0.0
        self.last_reranker_mode = "not_run"
        normalized = normalized_query or self.query_rewriter.rewrite(query)
        try:
            if self.vector_store.count() == 0:
                return await self._fallback_or_empty(query, normalized, top_k, scope, "empty_collection")

            embedding_started_at = perf_counter()
            query_embedding = self.embedder.embed(normalized)
            self.last_embedding_ms = (perf_counter() - embedding_started_at) * 1000

            query_started_at = perf_counter()
            candidates = self.vector_store.query(
                query_embedding,
                top_k=self.candidate_k,
                where=self._scope_to_where(scope),
            )
            self.last_vector_query_ms = (perf_counter() - query_started_at) * 1000
        except Exception:
            logger.exception("Vector retrieval failed; falling back to repository-backed RAG.")
            return await self._fallback_or_empty(query, normalized, top_k, scope, "vector_error")

        if not candidates:
            return await self._fallback_or_empty(query, normalized, top_k, scope, "no_candidates")

        documents: list[RetrievedDocument] = []
        for result in candidates:
            meta = result.metadata
            documents.append(
                RetrievedDocument(
                    title=meta.get("title", ""),
                    content=result.document,
                    snippet=result.document[:200],
                    source=meta.get("source", ""),
                    score=result.score,
                )
            )

        decision = self.reranker_gate.decide(
            scope=scope,
            candidate_count=len(documents),
            top_k=top_k,
        )
        rerank_started_at = perf_counter()
        if not decision.should_rerank:
            ranked = Reranker().rerank(query, documents, top_k=top_k)
            self.last_reranker_mode = f"skipped:{decision.reason}"
        else:
            try:
                ranked = self.reranker.rerank(query, documents, top_k=top_k)
                self.last_reranker_mode = str(
                    getattr(
                        self.reranker,
                        "last_mode",
                        getattr(self.reranker, "mode_name", type(self.reranker).__name__),
                    )
                )
            except Exception:
                logger.exception("Reranker failed outside its fallback wrapper; preserving vector order.")
                ranked = Reranker().rerank(query, documents, top_k=top_k)
                self.last_reranker_mode = "stable_order_fallback"
        self.last_rerank_ms = (perf_counter() - rerank_started_at) * 1000

        for item in ranked:
            item.document.score = item.score

        self.last_mode = "vector"
        logger.info(
            "Vector RAG retrieved %s candidates in %.2fms after %.2fms embedding; "
            "reranker=%s returned %s documents in %.2fms.",
            len(candidates),
            self.last_vector_query_ms,
            self.last_embedding_ms,
            self.last_reranker_mode,
            len(ranked),
            self.last_rerank_ms,
        )
        return [item.document for item in ranked]

    async def _fallback_or_empty(
        self,
        query: str,
        normalized_query: str,
        top_k: int,
        scope: RetrievalScope | None,
        reason: str,
    ) -> list[RetrievedDocument]:
        self.last_mode = f"fallback:{reason}"
        logger.warning("Vector RAG unavailable (%s); using repository-backed fallback.", reason)
        if self.fallback is None:
            return []
        return await self.fallback.retrieve(
            query,
            normalized_query=normalized_query,
            top_k=top_k,
            scope=scope,
        )

    @staticmethod
    def _scope_to_where(scope: RetrievalScope | None) -> dict | None:
        if scope is None or scope.is_empty():
            return None
        conditions: list[dict] = []
        if scope.source_entry_id is not None:
            conditions.append({"source_entry_id": scope.source_entry_id})
        if scope.category is not None:
            conditions.append({"category": scope.category})
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
