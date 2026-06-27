import json

from app.models.knowledge_chunk import KnowledgeChunk
from app.services.rag.index_builder import RAGIndexBuilder
from app.services.rag.vector_store import VectorStoreRecord


class FakeChunkRepository:
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks

    def list_all(self) -> list[KnowledgeChunk]:
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

    def replace_all(self, records: list[VectorStoreRecord]) -> int:
        self.records = list(records)
        return len(self.records)


def test_rag_index_builder_indexes_chunks_with_metadata() -> None:
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
            chunk_index=1,
            title="Lake View",
            category="attraction",
            content="A route-friendly scenic spot.",
            source="official_data_pack",
            metadata_json=None,
        ),
    ]
    vector_store = FakeVectorStore()

    report = RAGIndexBuilder(
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
