from __future__ import annotations

import asyncio

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_chunk import KnowledgeChunk
from app.repositories.knowledge import KnowledgeRepository
from app.services.rag.chroma_retriever import VectorBackedRAGService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.services.rag.retriever import RepositoryBackedRAGService
from app.services.rag.vector_store import VectorSearchResult
from app.tests.async_db import open_test_session


class FakeEmbedder:
    model_name = "fake"

    def embed(self, text: str) -> list[float]:
        return [0.1, float(len(text))]


class FixedVectorStore:
    collection_name = "stale-test"

    def __init__(self, document: str, metadata: dict) -> None:
        self.document = document
        self.metadata = metadata

    def count(self) -> int:
        return 1

    def query(self, *_args, **_kwargs):
        return [VectorSearchResult("ke_1_001", self.document, self.metadata, 1.0)]


def _make_entry(content: str) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=1,
        title="测试景点",
        category="景点信息",
        content=content,
        source="官方资料",
        aliases="",
        metadata_json=None,
    )


def test_vector_rag_replaces_stale_vector_text_with_current_database_revision() -> None:
    async def scenario():
        _engine, session = await open_test_session()
        try:
            entry = _make_entry("游客现在应看到的全新资料内容")
            session.add(entry)
            await session.flush()
            session.add(
                KnowledgeChunk(
                    chunk_id="ke_1_001",
                    source_entry_id=1,
                    chunk_index=1,
                    title=entry.title,
                    category=entry.category,
                    content=entry.content,
                    source=entry.source,
                    metadata_json="{}",
                )
            )
            await session.commit()

            fallback = RepositoryBackedRAGService(
                KnowledgeRepository(session), QueryRewriter(), Reranker()
            )
            service = VectorBackedRAGService(
                vector_store=FixedVectorStore(
                    "测试景点\n景点信息\n数据库里已被替换的旧内容",
                    {"chunk_id": "ke_1_001", "source_entry_id": 1, "title": "测试景点", "source": "官方资料"},
                ),
                embedder=FakeEmbedder(),
                query_rewriter=QueryRewriter(),
                reranker=Reranker(),
                fallback=fallback,
            )

            docs = await service.retrieve("全新资料内容", normalized_query="全新资料内容")
            assert any("全新资料内容" in doc.content for doc in docs)
            assert all("已被替换的旧内容" not in doc.content for doc in docs)
        finally:
            await session.close()
            await _engine.dispose()

    asyncio.run(scenario())


def test_vector_rag_hides_vector_content_after_knowledge_removal() -> None:
    async def scenario():
        _engine, session = await open_test_session()
        try:
            fallback = RepositoryBackedRAGService(
                KnowledgeRepository(session), QueryRewriter(), Reranker()
            )
            service = VectorBackedRAGService(
                vector_store=FixedVectorStore(
                    "已删除知识的旧内容",
                    {"chunk_id": "ke_1_001", "source_entry_id": 1, "title": "已删除景点", "source": "旧来源"},
                ),
                embedder=FakeEmbedder(),
                query_rewriter=QueryRewriter(),
                reranker=Reranker(),
                fallback=fallback,
            )

            docs = await service.retrieve("已删除景点", normalized_query="已删除景点")
            assert docs == []
        finally:
            await session.close()
            await _engine.dispose()

    asyncio.run(scenario())
