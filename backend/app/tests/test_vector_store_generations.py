from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from app.services.rag.vector_store import ChromaVectorStore, VectorStoreRecord


@dataclass
class FakeCollection:
    name: str
    records: dict[str, dict]
    fail_add: bool = False
    before_add: Callable[[], None] | None = None

    def count(self) -> int:
        return len(self.records)

    def add(self, *, ids, embeddings, documents, metadatas) -> None:
        if self.before_add is not None:
            self.before_add()
        if self.fail_add:
            raise RuntimeError("simulated index write failure")
        for item_id, embedding, document, metadata in zip(ids, embeddings, documents, metadatas, strict=True):
            self.records[item_id] = {
                "embedding": embedding,
                "document": document,
                "metadata": metadata,
            }

    def query(self, **_kwargs):
        selected = list(self.records.items())[:1]
        return {
            "ids": [[item_id for item_id, _ in selected]],
            "documents": [[row["document"] for _, row in selected]],
            "metadatas": [[row["metadata"] for _, row in selected]],
            "distances": [[0.0 for _ in selected]],
        }


class FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}
        self.fail_next_add = False
        self.before_next_add: Callable[[], None] | None = None

    def list_collections(self):
        return list(self.collections.values())

    def get_or_create_collection(self, *, name: str):
        if name not in self.collections:
            self.collections[name] = FakeCollection(
                name,
                {},
                fail_add=self.fail_next_add,
                before_add=self.before_next_add,
            )
            self.fail_next_add = False
            self.before_next_add = None
        return self.collections[name]

    def get_collection(self, name: str):
        return self.collections[name]

    def delete_collection(self, name: str):
        del self.collections[name]


def _record(item_id: str, document: str) -> VectorStoreRecord:
    return VectorStoreRecord(item_id, document, {"title": item_id}, [0.1, 0.2])


def _store(tmp_path) -> tuple[ChromaVectorStore, FakeClient]:
    store = ChromaVectorStore.__new__(ChromaVectorStore)
    store.persist_dir = tmp_path
    store.collection_name = "knowledge"
    client = FakeClient()
    store._client = client
    return store, client


def test_failed_index_generation_keeps_previous_generation_queryable(tmp_path) -> None:
    store, client = _store(tmp_path)
    store.replace_all([_record("old", "old document")])
    before = store.query([0.1, 0.2], top_k=1)
    old_generation_count = len(client.collections)
    client.fail_next_add = True

    with pytest.raises(RuntimeError, match="simulated index write failure"):
        store.replace_all([_record("new", "new document")])

    after = store.query([0.1, 0.2], top_k=1)
    assert store.count() == 1
    assert [item.id for item in after] == [item.id for item in before] == ["old"]
    assert len(client.collections) == old_generation_count


def test_successful_index_generation_switches_queries_to_new_contents(tmp_path) -> None:
    store, _client = _store(tmp_path)
    store.replace_all([_record("old", "old document")])

    store.replace_all([_record("new", "new document")])

    assert store.count() == 1
    assert [item.id for item in store.query([0.1, 0.2], top_k=1)] == ["new"]


def test_generation_pointer_is_reloaded_after_store_recreation(tmp_path) -> None:
    store, client = _store(tmp_path)
    store.replace_all([_record("new", "current document")])

    reopened = ChromaVectorStore.__new__(ChromaVectorStore)
    reopened.persist_dir = tmp_path
    reopened.collection_name = store.collection_name
    reopened._client = client

    assert reopened.count() == 1
    assert [item.id for item in reopened.query([0.1, 0.2], top_k=1)] == ["new"]


def test_empty_generation_can_be_activated_without_dropping_old_during_prepare(tmp_path) -> None:
    store, _client = _store(tmp_path)
    store.replace_all([_record("old", "current document")])

    assert store.replace_all([]) == 0

    assert store.count() == 0
    assert store.query([0.1, 0.2], top_k=1) == []


def test_queries_during_generation_build_continue_to_use_old_collection(tmp_path) -> None:
    store, client = _store(tmp_path)
    store.replace_all([_record("old", "old content")])
    observations: list[list[str]] = []
    client.before_next_add = lambda: observations.append(
        [item.id for item in store.query([0.1, 0.2], top_k=1)]
    )

    store.replace_all([_record("new", "new content")])

    assert observations == [["old"]]
    assert [item.id for item in store.query([0.1, 0.2], top_k=1)] == ["new"]
