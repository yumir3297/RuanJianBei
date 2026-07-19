from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.models.knowledge_chunk import KnowledgeChunk
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.services.rag.embedder import BaseEmbedder
from app.services.rag.vector_store import BaseVectorStore, MetadataValue, VectorStoreRecord


@dataclass(slots=True)
class RAGIndexBuildReport:
    total_chunks: int
    indexed_chunks: int
    collection_name: str
    embedding_model_name: str
    duration_ms: int


class RAGIndexBuilder:
    def __init__(
        self,
        chunk_repository: KnowledgeChunkRepository,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        *,
        batch_size: int = 32,
    ) -> None:
        self.chunk_repository = chunk_repository
        self.embedder = embedder
        self.vector_store = vector_store
        self.batch_size = max(batch_size, 1)

    async def build(self) -> RAGIndexBuildReport:
        started_at = perf_counter()
        chunks = await self.chunk_repository.list_all()
        records: list[VectorStoreRecord] = []

        for offset in range(0, len(chunks), self.batch_size):
            batch = chunks[offset : offset + self.batch_size]
            documents = [self._document_for(chunk) for chunk in batch]
            embeddings = self.embedder.embed_texts(documents)
            for chunk, document, embedding in zip(batch, documents, embeddings, strict=True):
                records.append(
                    VectorStoreRecord(
                        id=chunk.chunk_id,
                        document=document,
                        metadata=self._metadata_for(chunk),
                        embedding=embedding,
                    )
                )

        indexed_count = self.vector_store.replace_all(records)
        return RAGIndexBuildReport(
            total_chunks=len(chunks),
            indexed_chunks=indexed_count,
            collection_name=self.vector_store.collection_name,
            embedding_model_name=self.embedder.model_name,
            duration_ms=round((perf_counter() - started_at) * 1000),
        )

    def _document_for(self, chunk: KnowledgeChunk) -> str:
        return "\n".join([chunk.title, chunk.category, chunk.content])

    def _metadata_for(self, chunk: KnowledgeChunk) -> dict[str, MetadataValue]:
        metadata = self._decode_metadata(chunk.metadata_json)
        metadata.update(
            {
                "chunk_id": chunk.chunk_id,
                "title": chunk.title,
                "category": chunk.category,
                "source": chunk.source,
                "source_entry_id": chunk.source_entry_id,
                "chunk_index": chunk.chunk_index,
            }
        )
        return self._sanitize_metadata(metadata)

    def _decode_metadata(self, raw_metadata: str | None) -> dict[str, Any]:
        if not raw_metadata:
            return {}
        try:
            decoded = json.loads(raw_metadata)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, MetadataValue]:
        sanitized: dict[str, MetadataValue] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is not None:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
        return sanitized
