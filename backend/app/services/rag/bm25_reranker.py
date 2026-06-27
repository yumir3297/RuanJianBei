from __future__ import annotations

import re

from app.core.exceptions import AppError
from app.services.rag.base import RetrievedDocument
from app.services.rag.reranker import Reranker, RerankResult


_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+")


def tokenize_for_bm25(text: str) -> list[str]:
    tokens: list[str] = []
    for segment in _TOKEN_PATTERN.findall(text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            tokens.extend(segment)
            tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
        else:
            tokens.append(segment)
    return tokens


class BM25Reranker(Reranker):
    mode_name = "bm25"

    def __init__(self) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:
            raise AppError(
                "rank-bm25 is not installed. Install it before enabling BM25 fallback reranking.",
                error_code="reranker_dependency_missing",
                status_code=503,
            ) from exc
        self._bm25_class = BM25Okapi

    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[RerankResult]:
        if not documents or top_k <= 0:
            return []

        query_tokens = tokenize_for_bm25(query)
        corpus = [tokenize_for_bm25(document.content or document.snippet) for document in documents]
        if not query_tokens or not any(corpus):
            return super().rerank(query, documents, top_k=top_k)

        scores = self._bm25_class(corpus).get_scores(query_tokens)
        ranked = sorted(
            zip(documents, scores, strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        return [
            RerankResult(document=document, score=float(score))
            for document, score in ranked[:top_k]
        ]
