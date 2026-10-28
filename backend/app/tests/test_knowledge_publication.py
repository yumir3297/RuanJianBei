from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import knowledge_publications
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.services.knowledge.publication import KnowledgePublicationService
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.schemas.knowledge import KnowledgeUpdate
from app.tests.async_db import open_test_session


class FakeEmbedder:
    model_name = "fake-publication-embedder"

    def __init__(self, fail_on_call: int | None = None, fail_on_content: str | None = None) -> None:
        self.calls = 0
        self.fail_on_call = fail_on_call
        self.fail_on_content = fail_on_content

    def embed_texts(self, texts):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("embedding failed")
        if self.fail_on_content and any(self.fail_on_content in text for text in texts):
            raise RuntimeError("second entry embedding failed")
        return [[float(index + 1)] for index, _ in enumerate(texts)]


class FakeVectorStore:
    collection_name = "publication-test"

    def __init__(self) -> None:
        self.records = {}

    def upsert(self, records):
        self.records.update({record.id: record for record in records})
        return len(records)

    def delete_ids(self, ids):
        for item_id in ids:
            self.records.pop(item_id, None)


def _seed_drafts(path: str) -> list[tuple[int, str]]:
    async def scenario() -> list[tuple[int, str]]:
        engine, session = await open_test_session(path)
        try:
            selected = []
            for index in range(2):
                entry = KnowledgeEntry(
                    title=f"条目 {index}", category="景点信息", content=f"新内容 {index}", source="新 PDF"
                )
                session.add(entry)
                await session.flush()
                revision = KnowledgeRevision(
                    id=f"draft-{index}", knowledge_entry_id=entry.id, title=entry.title,
                    category=entry.category, content=entry.content, source=entry.source,
                )
                session.add(revision)
                await session.flush()
                entry.draft_revision_id = revision.id
                selected.append((entry.id, revision.id))
            session.add(KnowledgeState(id=1, epoch=1))
            await session.commit()
            return selected
        finally:
            await session.close()
            await engine.dispose()

    return asyncio.run(scenario())


def test_batch_publication_embedding_failure_keeps_every_entry_unpublished(tmp_path) -> None:
    db_path = str(tmp_path / "publication-failure.db")
    selected = _seed_drafts(db_path)
    vector_store = FakeVectorStore()

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(
                session, FakeEmbedder(fail_on_content="新内容 1"), vector_store
            )
            job = await service.create_publication(
                [
                    {"entry_id": entry_id, "revision_id": revision_id, "expected_version": 1}
                    for entry_id, revision_id in selected
                ],
                idempotency_key="batch-fails-on-prepare",
            )
            await service.run_publication(job.id)

            refreshed = [await session.get(KnowledgeEntry, entry_id) for entry_id, _ in selected]
            assert all(entry.published_revision_id is None for entry in refreshed)
            assert all(entry.draft_revision_id == revision_id for entry, (_, revision_id) in zip(refreshed, selected))
            failed = await service.get_publication(job.id)
            assert failed.state == "failed"
            assert "second entry embedding failed" in failed.error
            assert vector_store.records == {}
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_multiple_draft_edits_keep_published_base_for_publication(tmp_path) -> None:
    db_path = str(tmp_path / "publication-edited-draft.db")
    vector_store = FakeVectorStore()

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate

            workspace = KnowledgeWorkspaceService(session)
            entry, first = await workspace.save_draft(
                None,
                KnowledgeCreate(title="地点", category="景点信息", content="初稿", source="手册"),
            )
            entry, second = await workspace.save_draft(
                entry.id, KnowledgeUpdate(content="修改稿"), expected_version=entry.lock_version
            )
            assert first.base_revision_id is None
            assert second.base_revision_id is None
            job = await KnowledgePublicationService(session, FakeEmbedder(), vector_store).create_publication(
                [{"entry_id": entry.id, "revision_id": second.id, "expected_version": entry.lock_version}],
                idempotency_key="publish-latest-draft-edit",
            )
            await KnowledgePublicationService(session, FakeEmbedder(), vector_store).run_publication(job.id)
            await session.refresh(entry)
            assert entry.published_revision_id == second.id
            assert entry.content == "修改稿"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_successful_batch_switches_all_published_pointers_and_increments_epoch_once(tmp_path) -> None:
    db_path = str(tmp_path / "publication-success.db")
    selected = _seed_drafts(db_path)
    vector_store = FakeVectorStore()

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), vector_store)
            job = await service.create_publication(
                [
                    {"entry_id": entry_id, "revision_id": revision_id, "expected_version": 1}
                    for entry_id, revision_id in selected
                ],
                idempotency_key="batch-publish",
            )
            await service.run_publication(job.id)

            refreshed = [await session.get(KnowledgeEntry, entry_id) for entry_id, _ in selected]
            assert [entry.published_revision_id for entry in refreshed] == [revision_id for _, revision_id in selected]
            assert all(entry.draft_revision_id is None for entry in refreshed)
            assert (await session.get(KnowledgeState, 1)).epoch == 2
            assert (await service.get_publication(job.id)).state == "succeeded"
            assert len(vector_store.records) == 2
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_idempotency_key_returns_the_same_publication_job(tmp_path) -> None:
    db_path = str(tmp_path / "publication-idempotent.db")
    selected = _seed_drafts(db_path)

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            selection = [{"entry_id": selected[0][0], "revision_id": selected[0][1], "expected_version": 1}]
            first = await service.create_publication(selection, idempotency_key="same-request")
            second = await service.create_publication(selection, idempotency_key="same-request")
            assert first.id == second.id
            assert second.state == "queued"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_edit_after_click_preserves_the_later_draft_while_publishing_snapshot(tmp_path) -> None:
    db_path = str(tmp_path / "publication-continues-edit.db")
    selected = _seed_drafts(db_path)
    entry_id, selected_revision = selected[0]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            job = await service.create_publication(
                [{"entry_id": entry_id, "revision_id": selected_revision, "expected_version": 1}],
                idempotency_key="publish-click-snapshot",
            )
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            _, later_draft = await KnowledgeWorkspaceService(session).save_draft(
                entry_id,
                KnowledgeUpdate(content="发布期间继续编辑", expected_version=1),
                expected_version=1,
            )
            later_revision_id = later_draft.id
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            await service.run_publication(job.id)
            entry = await session.get(KnowledgeEntry, entry_id)
            assert entry.published_revision_id == selected_revision
            assert entry.draft_revision_id == later_revision_id
            assert (await service.get_publication(job.id)).state == "succeeded"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_withdrawal_wins_over_a_queued_publication_job(tmp_path) -> None:
    db_path = str(tmp_path / "publication-withdrawn.db")
    selected = _seed_drafts(db_path)
    entry_id, revision_id = selected[0]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            job = await service.create_publication(
                [{"entry_id": entry_id, "revision_id": revision_id, "expected_version": 1}],
                idempotency_key="withdraw-before-run",
            )
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            await KnowledgeWorkspaceService(session).withdraw(entry_id, expected_version=1)
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            await service.run_publication(job.id)
            entry = await session.get(KnowledgeEntry, entry_id)
            assert entry.published_revision_id is None
            assert entry.withdrawn_at is not None
            assert (await service.get_publication(job.id)).state == "failed"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_publication_api_creates_and_reads_persistent_job(tmp_path) -> None:
    db_path = str(tmp_path / "publication-api.db")
    selected = _seed_drafts(db_path)
    app = FastAPI()
    app.include_router(knowledge_publications.router, prefix="/api/knowledge-publications")

    async def override_session():
        engine, session = await open_test_session(db_path)
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_session
    token = create_admin_token(get_settings().admin_token_secret)
    client = TestClient(app)

    response = client.post(
        "/api/knowledge-publications/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "idempotency_key": "api-publication",
            "items": [
                {"entry_id": selected[0][0], "revision_id": selected[0][1], "expected_version": 1}
            ],
        },
    )
    assert response.status_code == 202
    job = response.json()
    assert job["state"] == "queued"

    read = client.get(
        f"/api/knowledge-publications/{job['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert read.status_code == 200
    assert read.json() == job


def test_competing_publications_cannot_overwrite_a_newer_published_revision(tmp_path) -> None:
    db_path = str(tmp_path / "publication-compete.db")
    selected = _seed_drafts(db_path)
    entry_id, first_revision_id = selected[0]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            first_job = await service.create_publication(
                [{"entry_id": entry_id, "revision_id": first_revision_id, "expected_version": 1}],
                idempotency_key="competing-publish-a",
            )
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            entry = await session.get(KnowledgeEntry, entry_id)
            second_revision = KnowledgeRevision(
                id="competing-branch",
                knowledge_entry_id=entry_id,
                base_revision_id=None,
                title=entry.title,
                category=entry.category,
                content="另一发布候选",
                source=entry.source,
            )
            session.add(second_revision)
            entry.draft_revision_id = second_revision.id
            entry.lock_version += 1
            await session.commit()
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            second_job = await service.create_publication(
                [{"entry_id": entry_id, "revision_id": second_revision.id, "expected_version": 2}],
                idempotency_key="competing-publish-b",
            )
            second_job_id = second_job.id
            await service.run_publication(first_job.id)
            await service.run_publication(second_job_id)

            entry = await session.get(KnowledgeEntry, entry_id)
            assert entry.published_revision_id == first_revision_id
            assert entry.draft_revision_id == second_revision.id
            assert (await service.get_publication(first_job.id)).state == "succeeded"
            assert (await service.get_publication(second_job_id)).state == "failed"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_expired_preparing_job_is_reclaimed_after_worker_restart(tmp_path) -> None:
    db_path = str(tmp_path / "publication-recovery.db")
    selected = _seed_drafts(db_path)
    entry_id, revision_id = selected[0]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            job = await service.create_publication(
                [{"entry_id": entry_id, "revision_id": revision_id, "expected_version": 1}],
                idempotency_key="recover-expired-job",
            )
            job.state = "preparing"
            job.lease_owner = "previous-process"
            job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()
            await service.run_publication(job.id)
            assert (await service.get_publication(job.id)).state == "succeeded"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_failed_job_can_be_retried_without_changing_its_snapshot(tmp_path) -> None:
    db_path = str(tmp_path / "publication-retry.db")
    selected = _seed_drafts(db_path)
    entry_id, revision_id = selected[0]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            failed_service = KnowledgePublicationService(session, FakeEmbedder(fail_on_call=1), FakeVectorStore())
            job = await failed_service.create_publication(
                [{"entry_id": entry_id, "revision_id": revision_id, "expected_version": 1}],
                idempotency_key="retry-same-snapshot",
            )
            job_id = job.id
            await failed_service.run_publication(job_id)
            assert (await failed_service.get_publication(job_id)).state == "failed"
            queued = await failed_service.retry_publication(job_id)
            assert queued.state == "queued"
            await session.close()

            await engine.dispose()
            engine, session = await open_test_session(db_path)
            service = KnowledgePublicationService(session, FakeEmbedder(), FakeVectorStore())
            await service.run_publication(job_id)
            assert (await service.get_publication(job_id)).state == "succeeded"
            entry = await session.get(KnowledgeEntry, entry_id)
            assert entry.published_revision_id == revision_id
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
