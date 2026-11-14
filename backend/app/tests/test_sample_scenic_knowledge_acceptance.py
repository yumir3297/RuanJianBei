from __future__ import annotations

import asyncio
import io
import json
from contextlib import nullcontext
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from starlette.datastructures import Headers

from app.core.config import Settings
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeState
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.knowledge.imports import KnowledgeImportService
from app.services.knowledge.publication import KnowledgePublicationService
from app.services.knowledge.visibility import VisibilityService
from app.tests.async_db import open_test_session


class _AcceptanceEmbedder:
    model_name = "sample-acceptance-fake"

    def embed_texts(self, texts):
        return [[float(index + 1)] for index, _ in enumerate(texts)]


class _AcceptanceVectorStore:
    collection_name = "sample-acceptance"

    def __init__(self) -> None:
        self.records = {}

    def write_guard(self):
        return nullcontext()

    def upsert(self, records):
        self.records.update({record.id: record for record in records})
        return len(records)

    def delete_ids(self, ids):
        for item_id in ids:
            self.records.pop(item_id, None)

    def count(self) -> int:
        return len(self.records)


def test_sample_scenic_knowledge_import_publish_visibility_round_trip(tmp_path) -> None:
    sample_path = Path(__file__).resolve().parents[3] / "data" / "processed" / "guide_sections.json"
    raw = sample_path.read_bytes()
    payload = json.loads(raw)
    expected_count = sum(
        1 for item in payload
        if isinstance(item, dict) and str(item.get("title", "")).strip() and str(item.get("content", "")).strip()
    )
    assert expected_count > 0
    db_path = str(tmp_path / "sample-scenic.db")

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            session.add(KnowledgeState(id=1, epoch=1)); await session.commit()
            settings = Settings(knowledge_upload_dir=str(tmp_path / "uploads"))
            upload = UploadFile(
                filename=sample_path.name,
                file=io.BytesIO(raw),
                headers=Headers({"content-type": "application/json"}),
            )
            importer = KnowledgeImportService(session, settings)
            batch = await importer.create_import(
                [upload], document_ids=[None], idempotency_key="sample-guide-sections-v1",
            )
            assert len(batch.jobs) == 1
            await importer.run_import(batch.jobs[0].id)
            batch = await importer.get_batch(batch.id)
            assert batch.state == "succeeded", batch.jobs[0].error

            drafts = list((await session.scalars(select(KnowledgeEntry))).all())
            assert len(drafts) == expected_count
            assert all(entry.draft_revision_id and entry.published_revision_id is None for entry in drafts)
            draft_refs = [(entry.id, entry.draft_revision_id) for entry in drafts]
            visibility = VisibilityService(session)
            assert await visibility.filter_published(draft_refs) == set()

            vector_store = _AcceptanceVectorStore()
            publisher = KnowledgePublicationService(session, _AcceptanceEmbedder(), vector_store)
            job = await publisher.create_publication(
                [
                    {
                        "entry_id": entry.id,
                        "revision_id": entry.draft_revision_id,
                        "expected_version": entry.lock_version,
                    }
                    for entry in drafts
                ],
                idempotency_key="sample-guide-sections-publish-v1",
            )
            await publisher.run_publication(job.id)
            assert (await publisher.get_publication(job.id)).state == "succeeded"

            # Dispose and reopen the SQLite engine so this checks persisted
            # state rather than only identity-map state in the same session.
            await session.close()
            await engine.dispose()
            engine, verify_session = await open_test_session(db_path)
            try:
                published = list((await verify_session.scalars(select(KnowledgeEntry))).all())
                assert len(published) == expected_count
                assert all(entry.published_revision_id and entry.draft_revision_id is None for entry in published)
                published_refs = [(entry.id, entry.published_revision_id) for entry in published]
                assert len(await VisibilityService(verify_session).filter_published(published_refs)) == expected_count
                chunks = list((await verify_session.scalars(select(KnowledgeChunk))).all())
                assert chunks and len(chunks) == vector_store.count()
            finally:
                await verify_session.close()
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
