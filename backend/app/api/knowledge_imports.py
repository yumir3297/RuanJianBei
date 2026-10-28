from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.knowledge_workspace import ImportConflict, KnowledgeRevision, SourceDocumentVersion
from app.schemas.knowledge_workspace import ImportBatchRead, ImportConflictRead, ImportConflictResolution, ImportJobRead, KnowledgeRevisionRead
from app.services.knowledge.imports import ImportBatchResult, KnowledgeImportService

router = APIRouter(dependencies=[Depends(require_admin_token)])


async def _to_read(batch: ImportBatchResult, session: AsyncSession) -> ImportBatchRead:
    jobs: list[ImportJobRead] = []
    for job in batch.jobs:
        version = (
            await session.get(SourceDocumentVersion, job.document_version_id)
            if job.document_version_id is not None
            else None
        )
        revision_result = await session.execute(
            select(KnowledgeRevision.knowledge_entry_id).where(
                KnowledgeRevision.source_document_version_id == job.document_version_id
            )
        ) if job.document_version_id else None
        conflict_result = await session.execute(
            select(ImportConflict).where(ImportConflict.job_id == job.id).order_by(ImportConflict.created_at)
        )
        conflicts = []
        for conflict in conflict_result.scalars().all():
            current = await session.get(KnowledgeRevision, conflict.current_revision_id) if conflict.current_revision_id else None
            incoming = await session.get(KnowledgeRevision, conflict.incoming_revision_id) if conflict.incoming_revision_id else None
            conflicts.append(
                ImportConflictRead(
                    id=conflict.id,
                    knowledge_entry_id=conflict.knowledge_entry_id,
                    current_revision_id=conflict.current_revision_id,
                    incoming_revision_id=conflict.incoming_revision_id,
                    kind=conflict.kind,
                    state=conflict.state,
                    current_revision=_revision_read(current),
                    incoming_revision=_revision_read(incoming),
                )
            )
        jobs.append(
            ImportJobRead(
                id=job.id,
                filename=job.original_filename,
                document_id=version.document_id if version else None,
                document_version_id=job.document_version_id,
                state=job.state,
                stage=job.stage,
                error=job.error,
                knowledge_entry_ids=sorted(set(revision_result.scalars().all())) if revision_result else [],
                conflicts=conflicts,
            )
        )
    return ImportBatchRead(id=batch.id, state=batch.state, stage=batch.stage, error=batch.error, jobs=jobs)


def _revision_read(revision: KnowledgeRevision | None) -> KnowledgeRevisionRead | None:
    if revision is None:
        return None
    return KnowledgeRevisionRead(
        id=revision.id,
        knowledge_entry_id=revision.knowledge_entry_id,
        title=revision.title,
        category=revision.category,
        content=revision.content,
        source=revision.source,
        aliases=[item for item in revision.aliases.split("|") if item],
        metadata_json=revision.metadata_json,
        created_at=revision.created_at,
    )


@router.post("/", response_model=ImportBatchRead, status_code=status.HTTP_202_ACCEPTED)
async def create_import(
    files: Annotated[list[UploadFile], File()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    document_ids: Annotated[list[str] | None, Form()] = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> ImportBatchRead:
    normalized_ids = [value or None for value in document_ids] if document_ids else None
    service = KnowledgeImportService(session, settings)
    result = await service.create_import(files, document_ids=normalized_ids, idempotency_key=idempotency_key)
    return await _to_read(result, session)


@router.get("/recent", response_model=list[ImportBatchRead])
async def list_recent_import_batches(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[ImportBatchRead]:
    batches = await KnowledgeImportService(session, settings).list_recent_batches()
    return [await _to_read(batch, session) for batch in batches]


@router.get("/{batch_id}", response_model=ImportBatchRead)
async def get_import_batch(
    batch_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> ImportBatchRead:
    batch = await KnowledgeImportService(session, settings).get_batch(batch_id)
    return await _to_read(batch, session)


@router.post("/{batch_id}/retry", response_model=ImportBatchRead, status_code=status.HTTP_202_ACCEPTED)
async def retry_import_batch(
    batch_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> ImportBatchRead:
    batch = await KnowledgeImportService(session, settings).retry_batch(batch_id)
    return await _to_read(batch, session)


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_import_conflict(
    conflict_id: str,
    payload: ImportConflictResolution,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    await KnowledgeImportService(session, settings).resolve_conflict(conflict_id, payload)
    return {"state": "resolved"}
