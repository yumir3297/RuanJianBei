from __future__ import annotations

import os
import uuid
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

    def prepare_all(self, records: Sequence[VectorStoreRecord]) -> str:
        """Write a new collection without making it active and return its name."""

    def activate_prepared(self, generation_name: str) -> None:
        """Make a previously prepared collection active."""

    def discard_prepared(self, generation_name: str) -> None:
        """Remove a prepared collection that will not be published."""

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
        collection_name = self._active_collection_name()
        if not self._collection_exists(collection_name):
            return 0
        return self._client.get_collection(collection_name).count()

    def replace_all(self, records: Sequence[VectorStoreRecord]) -> int:
        generation_name = self.prepare_all(records)
        try:
            self.activate_prepared(generation_name)
        except Exception:
            self.discard_prepared(generation_name)
            raise
        return len(records)

    def prepare_all(self, records: Sequence[VectorStoreRecord]) -> str:
        generation_name = f"idx_{uuid.uuid4().hex[:24]}"
        collection = self._client.get_or_create_collection(name=generation_name)
        try:
            if records:
                collection.add(
                    ids=[record.id for record in records],
                    embeddings=[record.embedding for record in records],
                    documents=[record.document for record in records],
                    metadatas=[record.metadata for record in records],
                )
        except Exception:
            self.discard_prepared(generation_name)
            raise
        return generation_name

    def activate_prepared(self, generation_name: str) -> None:
        if not self._collection_exists(generation_name):
            raise AppError(
                "Prepared RAG index collection no longer exists.",
                error_code="rag_prepared_index_missing",
                status_code=500,
            )
        self._activate_generation(generation_name)

    def discard_prepared(self, generation_name: str) -> None:
        if generation_name == self._active_collection_name():
            return
        try:
            self._client.delete_collection(generation_name)
        except Exception:
            pass

    def query(
        self,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        collection_name = self._active_collection_name()
        if top_k <= 0 or not self._collection_exists(collection_name):
            return []

        collection = self._client.get_collection(name=collection_name)
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

    @property
    def _active_pointer_path(self) -> Path:
        return self.persist_dir / f".{self.collection_name}.active"

    def _active_collection_name(self) -> str:
        try:
            active_name = self._active_pointer_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return self.collection_name
        return active_name or self.collection_name

    def _activate_generation(self, generation_name: str) -> None:
        pointer_path = self._active_pointer_path
        temporary_path = pointer_path.with_name(f"{pointer_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary_path.write_text(generation_name, encoding="utf-8")
            os.replace(temporary_path, pointer_path)
        finally:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    def _collection_exists(self, collection_name: str | None = None) -> bool:
        target_name = collection_name or self.collection_name
        existing = self._client.list_collections()
        names = {item if isinstance(item, str) else item.name for item in existing}
        return target_name in names
