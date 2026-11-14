import asyncio
import json
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.models.knowledge_chunk import KnowledgeChunk
from app.services.rag.index_builder import RAGIndexBuilder
from app.services.rag.vector_store import ChromaVectorStore, VectorStoreRecord


class FakeChunkRepository:
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks

    async def list_all(self) -> list[KnowledgeChunk]:
        return self._chunks


class FakeEmbedder:
    model_name = "fake-embedder"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]

    def embed(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class FakeVectorStore:
    collection_name = "fake_collection"

    def __init__(self) -> None:
        self.records: list[VectorStoreRecord] = []

    def write_guard(self):
        from contextlib import nullcontext
        return nullcontext()

    def replace_all(self, records: list[VectorStoreRecord]) -> int:
        self.records = list(records)
        return len(self.records)

    def prepare_all(self, records: list[VectorStoreRecord]) -> str:
        self.records = list(records)
        return "prepared"

    def activate_prepared(self, _generation_name: str) -> None:
        pass

    def discard_prepared(self, _generation_name: str) -> None:
        self.records = []


def test_rag_index_builder_indexes_chunks_with_metadata() -> None:
    async def scenario():
        chunks = [
            KnowledgeChunk(
                chunk_id="chunk_001",
                source_entry_id=7,
                chunk_index=1,
                title="Big Buddha",
                category="attraction",
                content="A landmark scenic area introduction.",
                source="official_data_pack",
                metadata_json=json.dumps({"source_title": "Big Buddha", "aliases": ["Buddha"]}),
            ),
            KnowledgeChunk(
                chunk_id="chunk_002",
                source_entry_id=8,
                revision_id="revision-8",
                chunk_index=1,
                title="Lake View",
                category="attraction",
                content="A route-friendly scenic spot.",
                source="official_data_pack",
                metadata_json=None,
            ),
        ]
        vector_store = FakeVectorStore()

        report = await RAGIndexBuilder(
            FakeChunkRepository(chunks),
            FakeEmbedder(),
            vector_store,
            batch_size=1,
        ).build()

        assert report.total_chunks == 2
        assert report.indexed_chunks == 2
        assert report.collection_name == "fake_collection"
        assert report.embedding_model_name == "fake-embedder"

        assert [record.id for record in vector_store.records] == ["chunk_001", "chunk_002"]
        assert vector_store.records[0].document.startswith("Big Buddha\nattraction\n")
        assert vector_store.records[0].metadata["source_entry_id"] == 7
        assert vector_store.records[0].metadata["source_title"] == "Big Buddha"
        assert vector_store.records[0].metadata["aliases"] == "[\"Buddha\"]"
        assert vector_store.records[1].metadata["chunk_id"] == "chunk_002"
        assert vector_store.records[1].metadata["revision_id"] == "revision-8"

    asyncio.run(scenario())


def test_rebuild_holds_writer_guard_from_snapshot_through_swap():
    class GuardedStore(FakeVectorStore):
        locked = False
        @asynccontextmanager
        async def write_guard(self):
            self.locked = True
            try: yield
            finally: self.locked = False
        def replace_all(self, records):
            assert self.locked
            return super().replace_all(records)

    store = GuardedStore()
    class GuardedRepo(FakeChunkRepository):
        async def list_all(self):
            assert store.locked
            return await super().list_all()

    chunk = KnowledgeChunk(chunk_id="c", source_entry_id=1, revision_id="r", chunk_index=1,
                           title="标题", category="景点", content="内容", source="资料")
    asyncio.run(RAGIndexBuilder(GuardedRepo([chunk]), FakeEmbedder(), store).build())
    assert not store.locked


def test_rebuild_serializes_publication_after_snapshot(tmp_path):
    """Shared local file lock and fake vector writes; not a real Chroma test."""
    from app.services.rag.index_write_lock import index_write_lock
    class InterleavedStore(FakeVectorStore):
        def write_guard(self):
            return index_write_lock(tmp_path / "index.lock", timeout=2)
        def upsert(self, records):
            self.records.extend(records)

    store = InterleavedStore()
    original = KnowledgeChunk(chunk_id="old", source_entry_id=1, revision_id="r1", chunk_index=1,
        title="旧条目", category="景点", content="内容", source="资料")
    published = VectorStoreRecord(id="new", document="新发布", metadata={}, embedding=[1.0, 0.0])

    async def scenario():
        snapshot_taken, release_snapshot = asyncio.Event(), asyncio.Event()
        attempting, published_done = asyncio.Event(), asyncio.Event()
        class PausedRepo(FakeChunkRepository):
            async def list_all(self):
                snapshot_taken.set()
                await release_snapshot.wait()
                return await super().list_all()
        async def publish():
            attempting.set()
            async with store.write_guard():
                store.upsert([published])
                published_done.set()
        rebuild = asyncio.create_task(RAGIndexBuilder(PausedRepo([original]), FakeEmbedder(), store).build())
        await snapshot_taken.wait()
        publication = asyncio.create_task(publish())
        await attempting.wait()
        await asyncio.sleep(0.1)
        assert not published_done.is_set()
        release_snapshot.set()
        await asyncio.gather(rebuild, publication)
        assert "new" in {record.id for record in store.records}

    asyncio.run(scenario())


class _FakeCollection:
    def __init__(self, name: str, *, fail_add: bool = False) -> None:
        self.name = name
        self.records = {}
        self.fail_add = fail_add

    def add(self, *, ids, embeddings, documents, metadatas):
        if self.fail_add:
            raise RuntimeError("staging write failed")
        self.records.update(dict(zip(ids, documents, strict=True)))

    def upsert(self, **kwargs):
        return self.add(**kwargs)

    def count(self):
        return len(self.records)


class _FakeChromaClient:
    def __init__(self, *, fail_add=False, fail_delete=False):
        self.collections = {"knowledge": _FakeCollection("knowledge")}
        self.fail_add = fail_add
        self.fail_delete = fail_delete

    def create_collection(self, *, name):
        collection = _FakeCollection(name, fail_add=self.fail_add)
        self.collections[name] = collection
        return collection

    def get_or_create_collection(self, *, name):
        return self.collections.setdefault(name, _FakeCollection(name))

    def get_collection(self, name):
        return self.collections[name]

    def delete_collection(self, name):
        if self.fail_delete and name == "knowledge":
            raise RuntimeError("old collection cleanup failed")
        self.collections.pop(name, None)

    def list_collections(self):
        return list(self.collections)


def _chroma_store(tmp_path, monkeypatch, client):
    monkeypatch.setitem(sys.modules, "chromadb", SimpleNamespace(PersistentClient=lambda path: client))
    return ChromaVectorStore(tmp_path, "knowledge")


def test_chroma_rebuild_failure_keeps_current_collection_and_pointer(tmp_path, monkeypatch) -> None:
    client = _FakeChromaClient(fail_add=True)
    store = _chroma_store(tmp_path, monkeypatch, client)
    client.collections["knowledge"].records["old"] = "old document"
    records = [VectorStoreRecord(id="new", document="new", metadata={}, embedding=[0.1])]

    try:
        store.replace_all(records)
    except RuntimeError as exc:
        assert "staging write failed" in str(exc)
    else:
        raise AssertionError("a failed staging write must fail the rebuild")

    assert store.collection_name == "knowledge"
    assert store.count() == 1
    assert (tmp_path / "knowledge.active").exists() is False


def test_chroma_rebuild_switches_pointer_before_best_effort_cleanup(tmp_path, monkeypatch) -> None:
    client = _FakeChromaClient(fail_delete=True)
    store = _chroma_store(tmp_path, monkeypatch, client)
    client.collections["knowledge"].records["old"] = "old document"
    records = [VectorStoreRecord(id="new", document="new", metadata={}, embedding=[0.1])]

    assert store.replace_all(records) == 1
    assert store.collection_name.startswith("knowledge_stage_")
    assert store.count() == 1
    assert "knowledge" in client.collections  # cleanup failure leaves old data recoverable


def test_chroma_rebuild_stops_before_writing_when_free_space_is_low(tmp_path, monkeypatch) -> None:
    from app.core.exceptions import AppError
    from app.services.rag import vector_store as vector_store_module

    client = _FakeChromaClient()
    store = _chroma_store(tmp_path, monkeypatch, client)
    client.collections["knowledge"].records["old"] = "old document"
    monkeypatch.setattr(vector_store_module.shutil, "disk_usage", lambda _: SimpleNamespace(free=1))
    try:
        store.replace_all([VectorStoreRecord(id="new", document="new", metadata={}, embedding=[0.1])])
    except AppError as exc:
        assert exc.error_code == "insufficient_storage"
    else:
        raise AssertionError("index rebuild must stop when staging space is unavailable")

    assert store.collection_name == "knowledge"
    assert store.count() == 1
    assert len(client.collections) == 1
