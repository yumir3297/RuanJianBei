from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
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

    def write_guard(self):
        """Serialize publication and index replacement for the shared store."""

    def count(self) -> int:
        """Return the number of records in the current collection."""

    def replace_all(self, records: Sequence[VectorStoreRecord]) -> int:
        """Build separately and atomically switch readers to the complete replacement."""

    def upsert(self, records: Sequence[VectorStoreRecord]) -> int:
        """Insert or replace only the supplied records."""

    def delete_ids(self, ids: Sequence[str]) -> None:
        """Remove specific records from the collection."""

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
        self.base_collection_name = collection_name
        self.pointer_path = self.persist_dir / f"{collection_name}.active"
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

    @property
    def collection_name(self) -> str:
        try:
            active = self.pointer_path.read_text(encoding="utf-8").strip()
        except OSError:
            active = ""
        if active and all(char.isalnum() or char in "._-" for char in active) and len(active) <= 63:
            return active
        return self.base_collection_name

    @collection_name.setter
    def collection_name(self, value: str) -> None:
        self.base_collection_name = value
        self.pointer_path = self.persist_dir / f"{value}.active"

    def write_guard(self):
        from app.services.rag.index_write_lock import index_lock_path, index_write_lock
        return index_write_lock(index_lock_path(self.persist_dir, self.base_collection_name))

    def count(self) -> int:
        if not self._collection_exists():
            return 0
        return self._client.get_collection(self.collection_name).count()

    def replace_all(self, records: Sequence[VectorStoreRecord]) -> int:
        staged_bytes = sum(
            len(record.document.encode("utf-8"))
            + len(json.dumps(record.metadata, ensure_ascii=False).encode("utf-8"))
            + len(record.embedding) * 4
            + 256
            for record in records
        )
        required_free = staged_bytes + 10 * 1024 * 1024
        if shutil.disk_usage(self.persist_dir).free < required_free:
            raise AppError(
                "Vector index storage is low on free space. Rebuild was stopped before switching collections.",
                error_code="insufficient_storage",
                status_code=507,
            )
        old_name = self.collection_name
        staging_name = f"{self.base_collection_name[:38]}_stage_{os.urandom(8).hex()}"
        create_collection = getattr(self._client, "create_collection", None)
        if create_collection is not None:
            collection = create_collection(name=staging_name)
        else:
            collection = self._client.get_or_create_collection(name=staging_name)
        temp_pointer = self.pointer_path.with_name(f"{self.pointer_path.name}.{os.urandom(6).hex()}.tmp")
        try:
            if records:
                for offset in range(0, len(records), 5000):
                    batch = records[offset : offset + 5000]
                    collection.add(
                        ids=[record.id for record in batch],
                        embeddings=[record.embedding for record in batch],
                        documents=[record.document for record in batch],
                        metadatas=[record.metadata for record in batch],
                    )
            temp_pointer.write_text(staging_name, encoding="utf-8")
            os.replace(temp_pointer, self.pointer_path)
        except Exception:
            try:
                temp_pointer.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                self._client.delete_collection(staging_name)
            except Exception:
                pass
            raise

        if old_name != staging_name:
            try:
                self._client.delete_collection(old_name)
            except Exception:
                # The pointer has already switched; cleanup can be retried later.
                pass
        return len(records)

    def upsert(self, records: Sequence[VectorStoreRecord]) -> int:
        if not records:
            return 0
        collection = self._client.get_or_create_collection(name=self.collection_name)
        collection.upsert(
            ids=[record.id for record in records],
            embeddings=[record.embedding for record in records],
            documents=[record.document for record in records],
            metadatas=[record.metadata for record in records],
        )
        return len(records)

    def delete_ids(self, ids: Sequence[str]) -> None:
        if ids and self._collection_exists():
            self._client.get_collection(self.collection_name).delete(ids=list(ids))

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
