from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_workspace import KnowledgeRevision
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.services.rag.index_builder import RAGIndexBuilder
from app.tests.async_db import open_test_session


class _Embedder:
    model_name = "workspace-e2e"

    def embed_texts(self, texts):
        return [[float(index + 1)] for index, _ in enumerate(texts)]


class _VectorStore:
    collection_name = "workspace-e2e"

    def __init__(self):
        self.records = []

    def write_guard(self):
        from contextlib import nullcontext
        return nullcontext()

    def replace_all(self, records):
        self.records = list(records)
        return len(self.records)


def test_index_rebuild_uses_only_current_published_nonwithdrawn_revisions(tmp_path) -> None:
    db_path = str(tmp_path / "workspace-index-e2e.db")

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            visible = KnowledgeEntry(title="已发布", category="景点信息", content="游客可见", source="手册")
            withdrawn = KnowledgeEntry(title="已下架", category="景点信息", content="不可见", source="手册")
            session.add_all([visible, withdrawn])
            await session.flush()

            visible_revision = KnowledgeRevision(
                id="visible-revision", knowledge_entry_id=visible.id, title=visible.title,
                category=visible.category, content=visible.content, source=visible.source,
            )
            draft_revision = KnowledgeRevision(
                id="draft-revision", knowledge_entry_id=visible.id, title=visible.title,
                category=visible.category, content="尚未發布", source=visible.source,
            )
            withdrawn_revision = KnowledgeRevision(
                id="withdrawn-revision", knowledge_entry_id=withdrawn.id, title=withdrawn.title,
                category=withdrawn.category, content=withdrawn.content, source=withdrawn.source,
            )
            session.add_all([visible_revision, draft_revision, withdrawn_revision])
            await session.flush()
            visible.published_revision_id = visible_revision.id
            visible.draft_revision_id = draft_revision.id
            withdrawn.published_revision_id = withdrawn_revision.id
            withdrawn.withdrawn_at = datetime.now(UTC)
            session.add_all(
                [
                    KnowledgeChunk(
                        chunk_id="visible-chunk", source_entry_id=visible.id, revision_id=visible_revision.id,
                        chunk_index=1, title=visible.title, category=visible.category, content=visible.content, source=visible.source,
                    ),
                    KnowledgeChunk(
                        chunk_id="draft-chunk", source_entry_id=visible.id, revision_id=draft_revision.id,
                        chunk_index=1, title=visible.title, category=visible.category, content="尚未發布", source=visible.source,
                    ),
                    KnowledgeChunk(
                        chunk_id="withdrawn-chunk", source_entry_id=withdrawn.id, revision_id=withdrawn_revision.id,
                        chunk_index=1, title=withdrawn.title, category=withdrawn.category, content=withdrawn.content, source=withdrawn.source,
                    ),
                ]
            )
            await session.commit()

            vector_store = _VectorStore()
            report = await RAGIndexBuilder(
                KnowledgeChunkRepository(session), _Embedder(), vector_store
            ).build()
            assert report.total_chunks == 1
            assert [record.id for record in vector_store.records] == ["visible-chunk"]
            assert vector_store.records[0].metadata["chunk_id"] == "visible-chunk"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
