"""Exercise the real local Chroma adapter with deterministic synthetic vectors."""
import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("chromadb", reason="real Chroma integration requires chromadb")

from app.services.rag.vector_store import ChromaVectorStore, VectorStoreRecord


def test_real_chroma_replace_filter_and_reopen_in_new_process(tmp_path):
    store = ChromaVectorStore(tmp_path, "guide_test")
    records = [
        VectorStoreRecord("a", "A", {"category": "history"}, [1.0, 0.0]),
        VectorStoreRecord("b", "B", {"category": "nature"}, [0.0, 1.0]),
    ]
    assert store.replace_all(records) == 2
    assert [item.id for item in store.query([1.0, 0.0], 2, {"category": "nature"})] == ["b"]
    store.upsert([VectorStoreRecord("c", "C", {"category": "history"}, [0.9, 0.1])])
    store.delete_ids(["a"])

    code = """
import json, sys
from pathlib import Path
from app.services.rag.vector_store import ChromaVectorStore
store = ChromaVectorStore(Path(sys.argv[1]), 'guide_test')
print(json.dumps({'count': store.count(), 'ids': [r.id for r in store.query([1.0, 0.0], 2)]}))
"""
    env = dict(os.environ, ANONYMIZED_TELEMETRY="False")
    completed = subprocess.run([sys.executable, "-c", code, str(tmp_path)], env=env,
                               capture_output=True, text=True, check=True, timeout=30)
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {"count": 2, "ids": ["c", "b"]}


def test_real_chroma_failed_replacement_preserves_active_index(tmp_path):
    store = ChromaVectorStore(tmp_path, "guide_failure")
    original = VectorStoreRecord("original", "old", {"category": "history"}, [1.0, 0.0])
    store.replace_all([original])
    active_before = store.collection_name
    duplicate = VectorStoreRecord("duplicate", "new", {"category": "nature"}, [0.0, 1.0])

    with pytest.raises(Exception):
        store.replace_all([duplicate, duplicate])

    assert store.collection_name == active_before
    assert [item.id for item in store.query([1.0, 0.0], 2)] == ["original"]
    assert {item.name for item in store._client.list_collections()} == {active_before}
