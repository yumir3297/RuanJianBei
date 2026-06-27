import asyncio

from app.services.rag.base import BaseRAGService, RetrievalScope, RetrievedDocument
from app.services.rag.chroma_retriever import VectorBackedRAGService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.services.rag.vector_store import VectorSearchResult


class FakeEmbedder:
    model_name = "fake-embedder"

    def __init__(self) -> None:
        self.embedded_texts: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.embedded_texts.append(text)
        return [0.1, 0.2]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class FakeVectorStore:
    collection_name = "fake_collection"

    def __init__(self, *, count: int = 1, fail_query: bool = False, result_count: int = 1) -> None:
        self.record_count = count
        self.fail_query = fail_query
        self.result_count = result_count
        self.last_top_k = 0
        self.last_where = None

    def count(self) -> int:
        return self.record_count

    def query(self, query_embedding: list[float], top_k: int, where=None) -> list[VectorSearchResult]:
        del query_embedding
        self.last_top_k = top_k
        self.last_where = where
        if self.fail_query:
            raise RuntimeError("vector store unavailable")
        return [
            VectorSearchResult(
                id=f"chunk_{index:03d}",
                document=f"Full scenic evidence {index} " + "A" * 220,
                metadata={"title": f"Scenic Spot {index}", "source": "official.docx"},
                score=0.87 - index * 0.01,
            )
            for index in range(self.result_count)
        ]


class FakeFallbackRAG(BaseRAGService):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, int]] = []

    async def retrieve(
        self,
        query: str,
        normalized_query: str | None = None,
        top_k: int = 5,
        scope: RetrievalScope | None = None,
    ) -> list[RetrievedDocument]:
        self.calls.append((query, normalized_query, top_k, scope))
        return [
            RetrievedDocument(
                title="Fallback",
                content="Repository fallback evidence",
                snippet="Repository fallback evidence",
                source="database",
                score=1.0,
            )
        ]


class FailingReranker(Reranker):
    def rerank(self, query, documents, top_k=5):
        del query, documents, top_k
        raise RuntimeError("reranker unavailable")


def build_service(
    vector_store: FakeVectorStore,
    fallback: FakeFallbackRAG,
) -> tuple[VectorBackedRAGService, FakeEmbedder]:
    embedder = FakeEmbedder()
    service = VectorBackedRAGService(
        vector_store=vector_store,
        embedder=embedder,
        query_rewriter=QueryRewriter(),
        reranker=Reranker(),
        fallback=fallback,
        candidate_k=20,
    )
    return service, embedder


def test_vector_rag_maps_full_content_and_uses_candidate_k() -> None:
    vector_store = FakeVectorStore()
    fallback = FakeFallbackRAG()
    service, embedder = build_service(vector_store, fallback)

    documents = asyncio.run(service.retrieve("scenic query", normalized_query="normalized", top_k=1))

    assert len(documents) == 1
    assert documents[0].title == "Scenic Spot 0"
    assert documents[0].content.startswith("Full scenic evidence")
    assert len(documents[0].snippet) == 200
    assert documents[0].source == "official.docx"
    assert documents[0].score == 0.87
    assert embedder.embedded_texts == ["normalized"]
    assert vector_store.last_top_k == 20
    assert fallback.calls == []
    assert service.last_mode == "vector"
    assert service.last_reranker_mode == "skipped:single_candidate"
    assert service.last_rerank_ms >= 0.0


def test_vector_rag_falls_back_when_collection_is_empty() -> None:
    vector_store = FakeVectorStore(count=0)
    fallback = FakeFallbackRAG()
    service, embedder = build_service(vector_store, fallback)

    documents = asyncio.run(service.retrieve("question", normalized_query="normalized", top_k=3))

    assert documents[0].title == "Fallback"
    assert fallback.calls == [("question", "normalized", 3, None)]
    assert embedder.embedded_texts == []
    assert service.last_mode == "fallback:empty_collection"


def test_vector_rag_falls_back_when_query_fails() -> None:
    vector_store = FakeVectorStore(fail_query=True)
    fallback = FakeFallbackRAG()
    service, embedder = build_service(vector_store, fallback)

    documents = asyncio.run(service.retrieve("question", normalized_query="normalized", top_k=2))

    assert documents[0].source == "database"
    assert fallback.calls == [("question", "normalized", 2, None)]
    assert embedder.embedded_texts == ["normalized"]
    assert service.last_mode == "fallback:vector_error"


def test_vector_rag_preserves_vector_order_when_unwrapped_reranker_fails() -> None:
    vector_store = FakeVectorStore(result_count=2)
    fallback = FakeFallbackRAG()
    service, _ = build_service(vector_store, fallback)
    service.reranker = FailingReranker()

    documents = asyncio.run(service.retrieve("question", normalized_query="normalized", top_k=1))

    assert documents[0].title == "Scenic Spot 0"
    assert documents[0].score == 0.87
    assert service.last_mode == "vector"
    assert service.last_reranker_mode == "stable_order_fallback"


def test_vector_rag_passes_selection_scope_to_vector_store() -> None:
    vector_store = FakeVectorStore()
    fallback = FakeFallbackRAG()
    service, _ = build_service(vector_store, fallback)

    asyncio.run(
        service.retrieve(
            "介绍一下",
            normalized_query="介绍一下",
            top_k=1,
            scope=RetrievalScope(source_entry_id=16),
        )
    )

    assert vector_store.last_where == {"source_entry_id": 16}
    assert service.last_reranker_mode == "skipped:single_candidate"


def test_vector_rag_skips_reranker_for_exact_scope_within_top_k() -> None:
    vector_store = FakeVectorStore(result_count=3)
    fallback = FakeFallbackRAG()
    service, _ = build_service(vector_store, fallback)
    service.reranker = FailingReranker()

    documents = asyncio.run(
        service.retrieve(
            "介绍一下",
            normalized_query="介绍一下",
            top_k=5,
            scope=RetrievalScope(source_entry_id=16),
        )
    )

    assert len(documents) == 3
    assert service.last_reranker_mode == "skipped:exact_scope_within_top_k"


def test_vector_rag_still_runs_reranker_without_exact_scope() -> None:
    vector_store = FakeVectorStore(result_count=5)
    fallback = FakeFallbackRAG()
    service, _ = build_service(vector_store, fallback)
    service.reranker = FailingReranker()

    asyncio.run(service.retrieve("question", normalized_query="normalized", top_k=5))

    assert service.last_reranker_mode == "stable_order_fallback"
