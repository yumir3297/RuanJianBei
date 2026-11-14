from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import (
    ImportBatch,
    ImportConflict,
    ImportJob,
    KnowledgeRevision,
    SourceDocument,
    SourceDocumentVersion,
)
from app.schemas.knowledge_workspace import ParsedSection
from app.schemas.knowledge_workspace import ImportConflictResolution
from app.services.knowledge.file_storage import KnowledgeFileStorage
from app.services.knowledge.import_diff import section_identity
from app.services.knowledge.parsers import BaseDocumentParser, parser_for_path
from app.services.knowledge.ocr import parse_pdf_with_optional_ocr

logger = logging.getLogger(__name__)
LEASE_SECONDS = 900


@dataclass(slots=True)
class ImportBatchResult:
    id: str
    state: str
    stage: str
    error: str | None
    jobs: list[ImportJob]


class KnowledgeImportService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        storage: KnowledgeFileStorage | None = None,
        parser: BaseDocumentParser | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage or KnowledgeFileStorage(settings)
        self.parser = parser

    async def resolve_conflict(self, conflict_id: str, resolution: ImportConflictResolution) -> None:
        conflict = await self.session.get(ImportConflict, conflict_id)
        if conflict is None:
            raise NotFoundError("Import conflict not found.")
        if conflict.state != "pending":
            raise AppError("This import conflict has already been resolved.", error_code="conflict_already_resolved", status_code=409)
        if conflict.knowledge_entry_id is None:
            raise AppError("This conflict cannot be attached to a knowledge entry.", error_code="invalid_import_conflict", status_code=409)
        entry = await self.session.get(KnowledgeEntry, conflict.knowledge_entry_id)
        if entry is None:
            raise NotFoundError("The conflicted knowledge entry no longer exists.")
        if entry.lock_version != resolution.expected_version:
            raise AppError("The knowledge entry changed. Reload it before resolving the conflict.", error_code="knowledge_version_conflict", status_code=409)

        if resolution.choice == "keep_current":
            conflict.state = "resolved"
            conflict.resolution_json = json.dumps({"choice": resolution.choice}, ensure_ascii=False)
            await self.session.commit()
            return

        incoming = await self.session.get(KnowledgeRevision, conflict.incoming_revision_id)
        if incoming is None:
            raise NotFoundError("The incoming source revision no longer exists.")
        if entry.draft_revision_id != conflict.current_revision_id:
            raise AppError("The current draft changed. Reload it before resolving the conflict.", error_code="knowledge_version_conflict", status_code=409)
        if resolution.choice == "use_incoming":
            revision = incoming
            revision.base_revision_id = entry.published_revision_id
        else:
            if resolution.merged_payload is None:
                raise AppError("A merged revision is required.", error_code="missing_merged_revision")
            payload = resolution.merged_payload
            revision = KnowledgeRevision(
                id=str(uuid4()),
                knowledge_entry_id=entry.id,
                base_revision_id=entry.published_revision_id,
                source_document_version_id=incoming.source_document_version_id,
                title=payload.title,
                category=payload.category,
                content=payload.content,
                source=payload.source,
                aliases="|".join(payload.aliases),
                metadata_json=payload.metadata_json,
                content_hash=hashlib.sha256(payload.content.encode("utf-8")).hexdigest(),
                page_start=incoming.page_start,
                page_end=incoming.page_end,
                section_path=incoming.section_path,
            )
            self.session.add(revision)
            await self.session.flush()

        entry.draft_revision_id = revision.id
        entry.title = revision.title
        entry.category = revision.category
        entry.content = revision.content
        entry.source = revision.source
        entry.aliases = revision.aliases
        entry.metadata_json = revision.metadata_json
        entry.lock_version += 1
        conflict.state = "resolved"
        conflict.resolution_json = json.dumps({"choice": resolution.choice, "revision_id": revision.id}, ensure_ascii=False)
        await self.session.commit()

    async def create_import(
        self,
        files: list[UploadFile],
        *,
        document_ids: list[str | None] | None = None,
        idempotency_key: str,
    ) -> ImportBatchResult:
        existing = await self._batch_by_key(idempotency_key)
        if existing is not None:
            return await self.get_batch(existing.id)
        if not files:
            raise AppError("Select at least one file to import.", error_code="empty_upload")
        if len(files) > self.settings.knowledge_import_max_files:
            raise AppError("Too many files in one import batch.", error_code="too_many_files", status_code=413)
        if document_ids is None:
            document_ids = [None] * len(files)
        if len(document_ids) != len(files):
            raise AppError("Each uploaded file must have one document ID slot.", error_code="invalid_document_ids")

        batch = ImportBatch(id=str(uuid4()), idempotency_key=idempotency_key, state="queued")
        self.session.add(batch)
        await self.session.flush()
        jobs: list[ImportJob] = []
        seen_versions: set[tuple[str, str]] = set()
        stored_paths: list[Path] = []

        for index, (upload, document_id) in enumerate(zip(files, document_ids, strict=True)):
            job = ImportJob(
                id=str(uuid4()),
                batch_id=batch.id,
                idempotency_key=f"{batch.id}:{index}",
                original_filename=self.storage._display_filename(upload.filename or "upload"),
                item_index=index,
                state="queued",
                stage="queued",
            )
            stored = None
            try:
                stored = await self.storage.store(upload)
                stored_paths.append(stored.path)
                if document_id:
                    document = await self.session.get(SourceDocument, document_id)
                    if document is None:
                        raise NotFoundError("The source document was not found.")
                else:
                    document = SourceDocument(id=str(uuid4()), name=stored.original_filename)
                    self.session.add(document)
                    await self.session.flush()

                version = await self._version_by_hash(document.id, stored.sha256)
                version_key = (document.id, stored.sha256)
                if version is None:
                    previous = await self._latest_version(document.id)
                    version = SourceDocumentVersion(
                        id=str(uuid4()),
                        document_id=document.id,
                        previous_version_id=previous.id if previous else None,
                        sha256=stored.sha256,
                        storage_path=str(stored.path.relative_to(self.storage.root)),
                        original_filename=stored.original_filename,
                        mime_type=stored.mime_type,
                        parse_status="queued",
                    )
                    self.session.add(version)
                    await self.session.flush()
                elif version.parse_status == "succeeded" or version_key in seen_versions:
                    job.state = "succeeded"
                    job.stage = "unchanged"
                    job.document_version_id = version.id
                    stored.path.unlink(missing_ok=True)
                    stored_paths.remove(stored.path)
                    jobs.append(job)
                    self.session.add(job)
                    seen_versions.add(version_key)
                    continue
                else:
                    active_job = await self.session.execute(
                        select(ImportJob.id).where(
                            ImportJob.document_version_id == version.id,
                            ImportJob.state.in_(["queued", "processing"]),
                        ).limit(1)
                    )
                    if active_job.scalar_one_or_none() is not None:
                        job.state = "succeeded"
                        job.stage = "unchanged_pending"
                        stored.path.unlink(missing_ok=True)
                        stored_paths.remove(stored.path)
                    else:
                        version.parse_status = "queued"
                        version.parse_error = None
                job.document_version_id = version.id
                seen_versions.add(version_key)
            except AppError as exc:
                if stored is not None:
                    stored.path.unlink(missing_ok=True)
                    if stored.path in stored_paths:
                        stored_paths.remove(stored.path)
                job.state = "failed"
                job.stage = exc.error_code
                job.error = f"{exc.error_code}: {exc.message}"
            except Exception as exc:
                if stored is not None:
                    stored.path.unlink(missing_ok=True)
                    if stored.path in stored_paths:
                        stored_paths.remove(stored.path)
                job.state = "failed"
                job.stage = "storage_failed"
                job.error = f"storage_failed: {exc}"
            self.session.add(job)
            jobs.append(job)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            for path in stored_paths:
                path.unlink(missing_ok=True)
            raced = await self._batch_by_key(idempotency_key)
            if raced is None:
                raise
            return await self.get_batch(raced.id)
        except Exception:
            await self.session.rollback()
            for path in stored_paths:
                path.unlink(missing_ok=True)
            raise
        await self.session.refresh(batch)
        await self._refresh_batch_state(batch.id)
        return await self.get_batch(batch.id)

    async def run_import(self, job_id: str) -> None:
        owner = str(uuid4())
        now = datetime.now(UTC)
        claim = await self.session.execute(
            update(ImportJob)
            .where(
                ImportJob.id == job_id,
                or_(
                    ImportJob.state == "queued",
                    (ImportJob.state == "processing") & (ImportJob.lease_until < now),
                ),
            )
            .values(
                state="processing",
                stage="parsing",
                lease_owner=owner,
                lease_until=now + timedelta(seconds=LEASE_SECONDS),
                error=None,
            )
        )
        await self.session.commit()
        if claim.rowcount != 1:
            return

        try:
            job = await self.session.get(ImportJob, job_id)
            if job is None or job.document_version_id is None:
                raise AppError("The import job has no stored document version.", error_code="missing_source_version")
            version = await self.session.get(SourceDocumentVersion, job.document_version_id)
            if version is None:
                raise NotFoundError("The stored source document version was not found.")
            stored_path = (self.storage.root / version.storage_path).resolve()
            if not stored_path.is_relative_to(self.storage.root.resolve()) or not stored_path.is_file():
                raise AppError("The stored source file is unavailable.", error_code="source_file_missing", status_code=404)
            parser = self.parser or parser_for_path(stored_path, max_pages=self.settings.knowledge_import_max_pages)
            try:
                parse = (lambda: parse_pdf_with_optional_ocr(parser, stored_path, self.settings)) if stored_path.suffix.lower() == ".pdf" and self.parser is None else (lambda: parser.parse(stored_path))
                sections = await asyncio.wait_for(
                    asyncio.to_thread(parse),
                    timeout=self.settings.knowledge_import_parse_timeout_seconds,
                )
            except TimeoutError as exc:
                raise AppError("Document parsing exceeded the time limit.", error_code="parse_timeout", status_code=422) from exc
            if not sections:
                raise AppError("The document contains no knowledge sections.", error_code="empty_document", status_code=422)
            if len(sections) > self.settings.knowledge_import_max_pages:
                raise AppError("The document has too many parsed sections.", error_code="too_many_pages", status_code=413)
            await self.session.rollback()
            await self._save_drafts(job_id, owner, sections)
        except Exception as exc:
            await self.session.rollback()
            await self._mark_failed(job_id, owner, exc)
            logger.exception("Knowledge import job %s failed", job_id)

    async def _save_drafts(self, job_id: str, owner: str, sections: list[ParsedSection]) -> None:
        await self.session.begin()
        job = await self.session.get(ImportJob, job_id)
        if job is None or job.lease_owner != owner or job.state != "processing":
            raise AppError("Import lease expired before draft creation.", error_code="import_lease_lost", status_code=409)
        version = await self.session.get(SourceDocumentVersion, job.document_version_id)
        if version is None:
            raise NotFoundError("The source document version no longer exists.")
        source_revisions_result = await self.session.execute(
            select(KnowledgeRevision)
            .join(SourceDocumentVersion, KnowledgeRevision.source_document_version_id == SourceDocumentVersion.id)
            # Human edits retain their source pointer for audit, but are not
            # source-derived baselines for automatic reimport matching.
            .where(SourceDocumentVersion.document_id == version.document_id, KnowledgeRevision.content_hash.is_not(None))
            .order_by(KnowledgeRevision.created_at.desc())
        )
        previous_by_identity: dict[str, KnowledgeRevision] = {}
        for previous_revision in source_revisions_result.scalars().all():
            identity = self._revision_identity(previous_revision)
            if identity and identity not in previous_by_identity:
                previous_by_identity[identity] = previous_revision

        for section in sections:
            identity = self._section_identity(section)
            previous_revision = previous_by_identity.get(identity)
            entry = (
                await self.session.get(KnowledgeEntry, previous_revision.knowledge_entry_id)
                if previous_revision is not None
                else None
            )
            content_hash = hashlib.sha256(section.content.encode("utf-8")).hexdigest()
            if previous_revision is not None and previous_revision.content_hash == content_hash:
                continue

            source_suffix = f" p.{section.page_start}" if section.page_start else ""
            source = (version.original_filename[: 255 - len(source_suffix)] + source_suffix)[:255]
            if entry is None:
                entry = KnowledgeEntry(
                    title=section.title,
                    category="待分类",
                    content=section.content,
                    source=source,
                    aliases="",
                    lock_version=1,
                )
                self.session.add(entry)
                await self.session.flush()
            revision = KnowledgeRevision(
                id=str(uuid4()),
                knowledge_entry_id=entry.id,
                base_revision_id=entry.published_revision_id,
                title=section.title,
                category="待分类",
                content=section.content,
                source=source,
                aliases="",
                metadata_json=json.dumps(
                    {
                        "source_document_id": version.document_id,
                        "sha256": version.sha256,
                        "section_identity": identity,
                        "stable_id": section.stable_id,
                        "extraction_method": section.extraction_method,
                    },
                    ensure_ascii=False,
                ),
                source_document_version_id=version.id,
                content_hash=content_hash,
                page_start=section.page_start,
                page_end=section.page_end,
                section_path=section.section_path,
            )
            self.session.add(revision)
            await self.session.flush()
            if previous_revision is not None and entry.draft_revision_id not in {
                None,
                previous_revision.id,
            }:
                self.session.add(
                    ImportConflict(
                        id=str(uuid4()),
                        job_id=job.id,
                        knowledge_entry_id=entry.id,
                        current_revision_id=entry.draft_revision_id,
                        incoming_revision_id=revision.id,
                        kind="content_changed",
                        state="pending",
                    )
                )
            else:
                entry.title = revision.title
                entry.category = revision.category
                entry.content = revision.content
                entry.source = revision.source
                entry.draft_revision_id = revision.id
                entry.lock_version += 1
        version.parse_status = "succeeded"
        version.parse_error = None
        job.state = "succeeded"
        job.stage = "drafts_created"
        job.error = None
        job.lease_owner = None
        job.lease_until = None
        await self.session.commit()
        await self._refresh_batch_state(job.batch_id)

    @staticmethod
    def _section_identity(section: ParsedSection) -> str:
        return section_identity(section)

    @staticmethod
    def _revision_identity(revision: KnowledgeRevision) -> str:
        if revision.metadata_json:
            try:
                identity = json.loads(revision.metadata_json).get("section_identity")
                if identity:
                    return str(identity).strip().casefold()
            except (json.JSONDecodeError, AttributeError):
                pass
        try:
            stable_id = json.loads(revision.metadata_json or "{}").get("stable_id")
        except (json.JSONDecodeError, AttributeError):
            stable_id = None
        if stable_id:
            return f"id:{str(stable_id).strip().casefold()}"
        return section_identity(ParsedSection(title=revision.title, content=revision.content, section_path=revision.section_path))

    async def _mark_failed(self, job_id: str, owner: str, error: Exception) -> None:
        job = await self.session.get(ImportJob, job_id)
        if job is None or job.lease_owner != owner:
            return
        error_code = getattr(error, "error_code", "parse_failed")
        message = getattr(error, "message", str(error))
        job.state = "failed"
        job.stage = "needs_ocr" if error_code == "needs_ocr" else "failed"
        job.error = f"{error_code}: {message}"[:4000]
        job.lease_owner = None
        job.lease_until = None
        if job.document_version_id:
            version = await self.session.get(SourceDocumentVersion, job.document_version_id)
            if version is not None:
                version.parse_status = "needs_ocr" if error_code == "needs_ocr" else "failed"
                version.parse_error = job.error
        await self.session.commit()
        await self._refresh_batch_state(job.batch_id)

    async def get_batch(self, batch_id: str) -> ImportBatchResult:
        batch = await self.session.get(ImportBatch, batch_id)
        if batch is None:
            raise NotFoundError("Import batch not found.")
        result = await self.session.execute(
            select(ImportJob)
            .where(ImportJob.batch_id == batch_id)
            .order_by(ImportJob.item_index.asc())
        )
        jobs = list(result.scalars().all())
        state = self._aggregate_state(jobs)
        stage = "queued" if state == "queued" else "completed" if state in {"succeeded", "partial", "failed"} else "processing"
        error = "; ".join(job.error for job in jobs if job.error) or None
        return ImportBatchResult(batch.id, state, stage, error, jobs)

    async def list_recent_batches(self, limit: int = 20) -> list[ImportBatchResult]:
        result = await self.session.execute(
            select(ImportBatch.id).order_by(ImportBatch.created_at.desc()).limit(max(1, min(limit, 50)))
        )
        return [await self.get_batch(batch_id) for batch_id in result.scalars().all()]

    async def retry_batch(self, batch_id: str) -> ImportBatchResult:
        batch = await self.session.get(ImportBatch, batch_id)
        if batch is None:
            raise NotFoundError("Import batch not found.")
        await self.session.execute(
            update(ImportJob)
            .where(ImportJob.batch_id == batch_id, ImportJob.state == "failed")
            .values(state="queued", stage="queued", error=None)
        )
        jobs_result = await self.session.execute(select(ImportJob).where(ImportJob.batch_id == batch_id))
        for job in jobs_result.scalars().all():
            if job.state == "queued" and job.document_version_id:
                version = await self.session.get(SourceDocumentVersion, job.document_version_id)
                if version is not None:
                    version.parse_status = "queued"
                    version.parse_error = None
        batch.state = "queued"
        batch.error = None
        await self.session.commit()
        return await self.get_batch(batch_id)

    async def pending_job_ids(self) -> list[str]:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(ImportJob.id)
            .where(
                or_(
                    ImportJob.state == "queued",
                    (ImportJob.state == "processing") & (ImportJob.lease_until < now),
                )
            )
            .order_by(ImportJob.created_at)
            .limit(20)
        )
        return list(result.scalars().all())

    async def _refresh_batch_state(self, batch_id: str | None) -> None:
        if batch_id is None:
            return
        batch = await self.session.get(ImportBatch, batch_id)
        if batch is None:
            return
        result = await self.session.execute(select(ImportJob).where(ImportJob.batch_id == batch_id))
        jobs = list(result.scalars().all())
        batch.state = self._aggregate_state(jobs)
        batch.error = "; ".join(job.error for job in jobs if job.error) or None
        await self.session.commit()

    @staticmethod
    def _aggregate_state(jobs: list[ImportJob]) -> str:
        if not jobs or all(job.state == "queued" for job in jobs):
            return "queued"
        if any(job.state in {"queued", "processing"} for job in jobs):
            return "processing"
        succeeded = any(job.state == "succeeded" for job in jobs)
        failed = any(job.state == "failed" for job in jobs)
        if succeeded and failed:
            return "partial"
        return "failed" if failed else "succeeded"

    async def _batch_by_key(self, idempotency_key: str) -> ImportBatch | None:
        result = await self.session.execute(
            select(ImportBatch).where(ImportBatch.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def _version_by_hash(self, document_id: str, sha256: str) -> SourceDocumentVersion | None:
        result = await self.session.execute(
            select(SourceDocumentVersion).where(
                SourceDocumentVersion.document_id == document_id,
                SourceDocumentVersion.sha256 == sha256,
            )
        )
        return result.scalar_one_or_none()

    async def _latest_version(self, document_id: str) -> SourceDocumentVersion | None:
        result = await self.session.execute(
            select(SourceDocumentVersion)
            .where(SourceDocumentVersion.document_id == document_id)
            .order_by(SourceDocumentVersion.created_at.desc(), SourceDocumentVersion.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
