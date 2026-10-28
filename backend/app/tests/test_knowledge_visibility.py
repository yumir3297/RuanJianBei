from __future__ import annotations

import asyncio
from datetime import datetime

from app.services.rag.base import BaseRAGService, RetrievedDocument
from app.services.rag.chroma_retriever import VectorBackedRAGService
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.services.rag.vector_store import VectorSearchResult
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.services.data_import.chunker import KnowledgeChunker
from app.services.knowledge.visibility import VisibilityService
from app.services.qa.cache import QACache
from app.tests.async_db import open_test_session
from sqlalchemy import update


class FakeEmbedder:
    model_name = "fake"

    def embed(self, text: str) -> list[float]:
        return [1.0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


class FakeVectorStore:
    collection_name = "fake"

    def __init__(self, results: list[VectorSearchResult]) -> None:
        self.results = results

    def count(self) -> int:
        return len(self.results)

    def query(self, query_embedding, top_k, where=None):
        return self.results[:top_k]


class FakeVisibility:
    def __init__(self, visible: set[tuple[int, str]]) -> None:
        self.visible = visible
        self.checked: list[list[tuple[int, str]]] = []

    async def filter_published(self, references: list[tuple[int, str]]) -> set[tuple[int, str]]:
        self.checked.append(references)
        return self.visible.intersection(references)


class FakeFallback(BaseRAGService):
    async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
        return [RetrievedDocument(title="数据库有效版本", content="已发布", entry_id=7, revision_id="current")]


def _result(entry_id: int, revision_id: str | None, title: str) -> VectorSearchResult:
    metadata = {"title": title, "source": "manual", "source_entry_id": entry_id}
    if revision_id is not None:
        metadata["revision_id"] = revision_id
    return VectorSearchResult("chunk", title, metadata, 0.9)


def test_vectors_are_filtered_against_the_published_revision() -> None:
    visibility = FakeVisibility({(1, "published")})
    service = VectorBackedRAGService(
        vector_store=FakeVectorStore([_result(1, "published", "有效"), _result(1, "draft", "草稿")]),
        embedder=FakeEmbedder(),
        query_rewriter=QueryRewriter(),
        reranker=Reranker(),
        fallback=FakeFallback(),
        visibility=visibility,
    )

    documents = asyncio.run(service.retrieve("景点", top_k=1))

    assert [document.title for document in documents] == ["有效"]
    assert (1, "draft") in visibility.checked[0]
    assert documents[0].revision_id == "published"


def test_stale_only_vectors_fall_back_to_database() -> None:
    service = VectorBackedRAGService(
        vector_store=FakeVectorStore([_result(7, "old", "旧版向量")]),
        embedder=FakeEmbedder(),
        query_rewriter=QueryRewriter(),
        reranker=Reranker(),
        fallback=FakeFallback(),
        visibility=FakeVisibility(set()),
    )

    documents = asyncio.run(service.retrieve("景点", top_k=1))

    assert [document.title for document in documents] == ["数据库有效版本"]
    assert service.last_mode == "fallback:no_published_vectors"


def test_vectors_without_revision_metadata_are_never_returned() -> None:
    service = VectorBackedRAGService(
        vector_store=FakeVectorStore([_result(7, None, "无版本信息")]),
        embedder=FakeEmbedder(),
        query_rewriter=QueryRewriter(),
        reranker=Reranker(),
        fallback=FakeFallback(),
        visibility=FakeVisibility(set()),
    )

    documents = asyncio.run(service.retrieve("景点", top_k=1))

    assert [document.title for document in documents] == ["数据库有效版本"]


class MemoryDBCache:
    def __init__(self) -> None:
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, answer, sources, expires_at):
        from types import SimpleNamespace

        value = SimpleNamespace(answer=answer, sources=__import__("json").dumps(sources), expires_at=expires_at)
        self.values[key] = value
        return value

    async def invalidate(self, key=None):
        if key is None:
            self.values.clear()
        else:
            self.values.pop(key, None)


def test_old_memory_and_database_answers_are_invisible_after_epoch_changes() -> None:
    async def scenario() -> None:
        repository = MemoryDBCache()
        cache = QACache(repository, ttl_seconds=60)
        await cache.set("faq:开放时间", "旧 FAQ 答案", [], epoch=8)
        assert (await cache.get("faq:开放时间", epoch=8)).answer == "旧 FAQ 答案"

        # Simulate another request/process after publication or withdrawal.
        fresh_process_cache = QACache(repository, ttl_seconds=60)
        assert await fresh_process_cache.get("faq:开放时间", epoch=9) is None

        # A slow request captured at epoch 8 may finish later, but cannot
        # overwrite or populate the namespace used by epoch 9 requests.
        await cache.set("faq:开放时间", "旧请求迟到结果", [], epoch=8)
        assert await fresh_process_cache.get("faq:开放时间", epoch=9) is None

    asyncio.run(scenario())


def test_visibility_service_reads_durable_epoch_and_only_current_publications(tmp_path) -> None:
    db_path = str(tmp_path / "visibility.db")

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            visible_entry = KnowledgeEntry(title="景点", category="景点信息", content="当前", source="手册")
            withdrawn_entry = KnowledgeEntry(title="下架", category="景点信息", content="旧", source="手册")
            session.add_all([visible_entry, withdrawn_entry])
            await session.flush()
            current = KnowledgeRevision(
                id="current", knowledge_entry_id=visible_entry.id, title="景点", category="景点信息",
                content="当前", source="手册",
            )
            stale = KnowledgeRevision(
                id="stale", knowledge_entry_id=visible_entry.id, title="景点", category="景点信息",
                content="过期", source="手册",
            )
            withdrawn = KnowledgeRevision(
                id="withdrawn", knowledge_entry_id=withdrawn_entry.id, title="下架", category="景点信息",
                content="旧", source="手册",
            )
            session.add_all([current, stale, withdrawn])
            await session.flush()
            visible_entry.published_revision_id = current.id
            visible_entry.draft_revision_id = stale.id
            withdrawn_entry.published_revision_id = withdrawn.id
            withdrawn_entry.withdrawn_at = datetime.now().astimezone()
            session.add(KnowledgeState(id=1, epoch=4))
            await session.commit()

            visibility = VisibilityService(session)
            assert await visibility.read_epoch() == 4
            await session.execute(update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=5))
            await session.commit()
            assert await visibility.read_epoch() == 5
            assert await visibility.filter_published(
                [(visible_entry.id, "current"), (visible_entry.id, "stale"), (withdrawn_entry.id, "withdrawn")]
            ) == {(visible_entry.id, "current")}
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_published_chunks_include_revision_in_id_and_metadata() -> None:
    entry = KnowledgeEntry(
        id=42,
        title="灵山大佛",
        category="景点信息",
        content="官方介绍。",
        source="手册",
        aliases="大佛",
        published_revision_id="revision-abc",
    )

    chunks = KnowledgeChunker().build_chunks([entry])

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "ke_42_revision-abc_001"
    assert chunks[0].revision_id == "revision-abc"
