from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Sequence
from uuid import uuid4

from sqlalchemy import case, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_workspace import (
    KnowledgeRevision,
    KnowledgeState,
    PublicationItem,
    PublicationJob,
)
from app.schemas.knowledge_workspace import PublicationSelection
from app.services.data_import.chunker import KnowledgeChunker
from app.services.rag.embedder import BaseEmbedder
from app.services.rag.vector_store import BaseVectorStore, MetadataValue, VectorStoreRecord

logger = logging.getLogger(__name__)
LEASE_SECONDS = 900


class KnowledgePublicationService:
    def __init__(
        self,
        session: AsyncSession,
        embedder: BaseEmbedder | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.session = session
        self.embedder = embedder
        self.vector_store = vector_store

    async def create_publication(
        self,
        items: Sequence[PublicationSelection | dict],
        *,
        idempotency_key: str,
    ) -> PublicationJob:
        existing = await self._job_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        selections = [
            item if isinstance(item, PublicationSelection) else PublicationSelection.model_validate(item)
            for item in items
        ]
        if not selections or len({item.entry_id for item in selections}) != len(selections):
            raise AppError("Choose at least one unique knowledge entry.", error_code="invalid_publication")

        job = PublicationJob(id=str(uuid4()), idempotency_key=idempotency_key, state="queued")
        self.session.add(job)
        await self.session.flush()
        for selection in selections:
            entry = await self.session.get(KnowledgeEntry, selection.entry_id)
            revision = await self.session.get(KnowledgeRevision, selection.revision_id)
            if entry is None or revision is None or revision.knowledge_entry_id != selection.entry_id:
                raise NotFoundError("The selected knowledge draft was not found.")
            if entry.withdrawn_at is not None:
                raise AppError("Withdrawn knowledge cannot be published.", error_code="knowledge_withdrawn", status_code=409)
            if entry.lock_version != selection.expected_version or entry.draft_revision_id != selection.revision_id:
                raise AppError("The selected draft changed. Reload it before publishing.", error_code="knowledge_version_conflict", status_code=409)
            self.session.add(
                PublicationItem(
                    id=str(uuid4()),
                    job_id=job.id,
                    knowledge_entry_id=entry.id,
                    revision_id=revision.id,
                    expected_lock_version=selection.expected_version,
                    state="queued",
                )
            )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raced = await self._job_by_idempotency_key(idempotency_key)
            if raced is None:
                raise
            return raced
        await self.session.refresh(job)
        return job

    async def run_publication(self, job_id: str) -> None:
        owner = str(uuid4())
        now = datetime.now(UTC)
        claim = await self.session.execute(
            update(PublicationJob)
            .where(
                PublicationJob.id == job_id,
                or_(
                    PublicationJob.state == "queued",
                    (PublicationJob.state == "preparing") & (PublicationJob.lease_until < now),
                ),
            )
            .values(
                state="preparing",
                lease_owner=owner,
                lease_until=now + timedelta(seconds=LEASE_SECONDS),
                error=None,
            )
        )
        await self.session.commit()
        if claim.rowcount != 1:
            return
        await self.session.execute(
            update(PublicationItem).where(PublicationItem.job_id == job_id).values(state="preparing", error=None)
        )
        await self.session.commit()

        try:
            if self.embedder is None or self.vector_store is None:
                raise AppError("Publication workers are not configured.", error_code="publication_worker_unavailable", status_code=503)
            job, items = await self._load_job_items(job_id)
            if job is None:
                raise NotFoundError("Publication job not found.")
            records, chunks = await self._prepare(items)
            commit_items = [
                (item.id, item.knowledge_entry_id, item.revision_id, item.expected_lock_version)
                for item, _, _ in items
            ]
            if records:
                await asyncio.to_thread(self.vector_store.upsert, records)

            # Drop the preparation read transaction before the short commit transaction.
            await self.session.rollback()
            await self._commit_publication(job_id, owner, commit_items, chunks)
        except Exception as exc:
            await self.session.rollback()
            await self._mark_failed(job_id, owner, exc)
            logger.exception("Knowledge publication %s failed during preparation or commit", job_id)

    async def _prepare(
        self, items: list[tuple[PublicationItem, KnowledgeEntry, KnowledgeRevision]]
    ) -> tuple[list[VectorStoreRecord], list[KnowledgeChunk]]:
        chunker = KnowledgeChunker()
        chunks: list[KnowledgeChunk] = []
        for item, entry, revision in items:
            if entry.withdrawn_at is not None:
                raise AppError("A selected entry was withdrawn before publication.", error_code="knowledge_withdrawn", status_code=409)
            if revision.base_revision_id != entry.published_revision_id:
                raise AppError("The selected draft is based on an older published version.", error_code="knowledge_version_conflict", status_code=409)
            snapshot = SimpleNamespace(
                id=entry.id,
                title=revision.title,
                category=revision.category,
                content=revision.content,
                source=revision.source,
                aliases=revision.aliases,
                metadata_json=revision.metadata_json,
                published_revision_id=revision.id,
            )
            chunks.extend(chunker.build_chunks([snapshot]))

        if not chunks:
            raise AppError("The selected drafts contain no indexable text.", error_code="empty_publication")
        documents = ["\n".join([chunk.title, chunk.category, chunk.content]) for chunk in chunks]
        if self.embedder is None:
            raise AppError("Publication workers are not configured.", error_code="publication_worker_unavailable", status_code=503)
        embeddings = await asyncio.to_thread(self.embedder.embed_texts, documents)
        if len(embeddings) != len(chunks):
            raise AppError("Embedding count did not match prepared knowledge chunks.", error_code="embedding_mismatch")
        records = [
            VectorStoreRecord(
                id=chunk.chunk_id,
                document=document,
                metadata=self._metadata_for(chunk),
                embedding=embedding,
            )
            for chunk, document, embedding in zip(chunks, documents, embeddings, strict=True)
        ]
        return records, chunks

    async def _commit_publication(
        self,
        job_id: str,
        owner: str,
        original_items: list[tuple[str, int, str, int]],
        chunks: list[KnowledgeChunk],
    ) -> None:
        await self.session.begin()
        job = await self.session.get(PublicationJob, job_id)
        if job is None or job.lease_owner != owner or job.state != "preparing":
            raise AppError("Publication lease expired before commit.", error_code="publication_lease_lost", status_code=409)
        for item_id, entry_id, revision_id, expected_lock_version in original_items:
            entry = await self.session.get(KnowledgeEntry, entry_id)
            revision = await self.session.get(KnowledgeRevision, revision_id)
            if entry is None or revision is None or revision.knowledge_entry_id != entry_id:
                raise AppError("A selected draft no longer exists.", error_code="knowledge_version_conflict", status_code=409)
            if entry.withdrawn_at is not None:
                raise AppError("A selected entry was withdrawn before publication.", error_code="knowledge_withdrawn", status_code=409)
            if revision.base_revision_id != entry.published_revision_id:
                raise AppError("Another publication changed the published version.", error_code="knowledge_version_conflict", status_code=409)
            if expected_lock_version > entry.lock_version:
                raise AppError("The knowledge entry version moved backwards.", error_code="knowledge_version_conflict", status_code=409)

            switched = await self.session.execute(
                update(KnowledgeEntry)
                .where(
                    KnowledgeEntry.id == entry_id,
                    KnowledgeEntry.published_revision_id == revision.base_revision_id,
                    KnowledgeEntry.withdrawn_at.is_(None),
                )
                .values(
                    published_revision_id=revision.id,
                    title=revision.title,
                    category=revision.category,
                    content=revision.content,
                    source=revision.source,
                    aliases=revision.aliases,
                    metadata_json=revision.metadata_json,
                    draft_revision_id=case(
                        (KnowledgeEntry.draft_revision_id == revision.id, None),
                        else_=KnowledgeEntry.draft_revision_id,
                    ),
                    lock_version=KnowledgeEntry.lock_version + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if switched.rowcount != 1:
                raise AppError("Another publication or withdrawal won the race.", error_code="knowledge_version_conflict", status_code=409)
            entry.published_revision_id = revision.id
            entry.title = revision.title
            entry.category = revision.category
            entry.content = revision.content
            entry.source = revision.source
            entry.aliases = revision.aliases
            entry.metadata_json = revision.metadata_json
            if entry.draft_revision_id == revision.id:
                entry.draft_revision_id = None
            entry.lock_version += 1

            item = await self.session.get(PublicationItem, item_id)
            if item is not None:
                item.state = "succeeded"
                item.error = None

        self.session.add_all(chunks)
        state_update = await self.session.execute(
            update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch + 1)
        )
        if state_update.rowcount == 0:
            self.session.add(KnowledgeState(id=1, epoch=2))
        job.state = "committing"
        await self.session.flush()
        job.state = "succeeded"
        job.error = None
        job.lease_owner = None
        job.lease_until = None
        await self.session.commit()

    async def _load_job_items(
        self, job_id: str
    ) -> tuple[PublicationJob | None, list[tuple[PublicationItem, KnowledgeEntry, KnowledgeRevision]]]:
        job = await self.session.get(PublicationJob, job_id)
        result = await self.session.execute(
            select(PublicationItem, KnowledgeEntry, KnowledgeRevision)
            .join(KnowledgeEntry, KnowledgeEntry.id == PublicationItem.knowledge_entry_id)
            .join(KnowledgeRevision, KnowledgeRevision.id == PublicationItem.revision_id)
            .where(PublicationItem.job_id == job_id)
            .order_by(PublicationItem.knowledge_entry_id)
        )
        return job, list(result.all())

    async def _mark_failed(self, job_id: str, owner: str, error: Exception) -> None:
        job = await self.session.get(PublicationJob, job_id)
        if job is None or job.lease_owner != owner:
            return
        job.state = "failed"
        job.error = str(error)[:4000]
        job.lease_owner = None
        job.lease_until = None
        result = await self.session.execute(select(PublicationItem).where(PublicationItem.job_id == job_id))
        for item in result.scalars().all():
            if item.state != "succeeded":
                item.state = "failed"
                item.error = job.error
        await self.session.commit()

    async def get_publication(self, job_id: str) -> PublicationJob:
        job = await self.session.get(PublicationJob, job_id)
        if job is None:
            raise NotFoundError("Publication job not found.")
        return job

    async def retry_publication(self, job_id: str) -> PublicationJob:
        job = await self.get_publication(job_id)
        if job.state != "failed":
            raise AppError("Only failed publication jobs can be retried.", error_code="publication_not_retryable", status_code=409)
        job.state = "queued"
        job.error = None
        await self.session.execute(
            update(PublicationItem)
            .where(PublicationItem.job_id == job_id)
            .values(state="queued", error=None)
        )
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def pending_job_ids(self) -> list[str]:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(PublicationJob.id)
            .where(
                or_(
                    PublicationJob.state == "queued",
                    (PublicationJob.state == "preparing") & (PublicationJob.lease_until < now),
                )
            )
            .order_by(PublicationJob.created_at)
            .limit(20)
        )
        return list(result.scalars().all())

    @staticmethod
    def _metadata_for(chunk: KnowledgeChunk) -> dict[str, MetadataValue]:
        metadata: dict[str, MetadataValue] = {
            "chunk_id": chunk.chunk_id,
            "source_entry_id": chunk.source_entry_id,
            "revision_id": chunk.revision_id or "",
            "title": chunk.title,
            "category": chunk.category,
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
        }
        try:
            decoded = json.loads(chunk.metadata_json or "{}")
        except json.JSONDecodeError:
            decoded = {}
        if isinstance(decoded, dict):
            for key, value in decoded.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
                elif value is not None:
                    metadata[key] = json.dumps(value, ensure_ascii=False)
        return metadata

    async def _job_by_idempotency_key(self, key: str) -> PublicationJob | None:
        result = await self.session.execute(
            select(PublicationJob).where(PublicationJob.idempotency_key == key)
        )
        return result.scalar_one_or_none()
