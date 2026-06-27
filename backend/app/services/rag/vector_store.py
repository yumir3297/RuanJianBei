from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from app.core.exceptions import AppError


MetadataValue = str | int | float | bool


@dataclass(slots=True)
class VectorStoreRecord:
    id: str
    document: str
    metadata: dict[str, MetadataValue]
    embedding: list[float]


@dataclass(slots=True)
class VectorSearchResult:
    id: str
    document: str
    metadata: dict[str, Any]
    score: float


class BaseVectorStore(Protocol):
    collection_name: str

    def count(self) -> int:
        """Return the number of records in the current collection."""

    def replace_all(self, records: Sequence[VectorStoreRecord]) -> int:
        """Replace the whole vector collection with the supplied records."""

    def query(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Return top vector matches for an embedded query."""


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
        except ImportError as exc:
            raise AppError(
                "ChromaDB is not installed. Install chromadb before building the RAG index.",
                error_code="rag_dependency_missing",
                status_code=503,
            ) from exc

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))

    def count(self) -> int:
        if not self._collection_exists():
            return 0
        return self._client.get_collection(self.collection_name).count()

    def replace_all(self, records: Sequence[VectorStoreRecord]) -> int:
        if self._collection_exists():
            self._client.delete_collection(self.collection_name)

        collection = self._client.get_or_create_collection(name=self.collection_name)
        if not records:
            return 0

        collection.add(
            ids=[record.id for record in records],
            embeddings=[record.embedding for record in records],
            documents=[record.document for record in records],
            metadatas=[record.metadata for record in records],
        )
        return len(records)

    def query(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if top_k <= 0 or not self._collection_exists():
            return []

        collection = self._client.get_collection(name=self.collection_name)
        record_count = collection.count()
        if record_count == 0:
            return []

        query_args: dict[str, Any] = {
            "query_embeddings": [list(query_embedding)],
            "n_results": min(top_k, record_count),
        }
        if where:
            query_args["where"] = where
        result = collection.query(**query_args)

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matches: list[VectorSearchResult] = []
        for index, item_id in enumerate(ids):
            distance = distances[index] if index < len(distances) else None
            score = 0.0 if distance is None else 1 / (1 + float(distance))
            matches.append(
                VectorSearchResult(
                    id=str(item_id),
                    document=str(documents[index] if index < len(documents) else ""),
                    metadata=dict(metadatas[index] if index < len(metadatas) and metadatas[index] else {}),
                    score=score,
                )
            )
        return matches

    def _collection_exists(self) -> bool:
        existing = self._client.list_collections()
        names = {item if isinstance(item, str) else item.name for item in existing}
        return self.collection_name in names
