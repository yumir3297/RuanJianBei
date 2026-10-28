from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.knowledge_workspace import SourceDocumentVersion
from app.schemas.knowledge_workspace import ImportBatchRead, ImportJobRead
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
        jobs.append(
            ImportJobRead(
                id=job.id,
                filename=job.original_filename,
                document_id=version.document_id if version else None,
                document_version_id=job.document_version_id,
                state=job.state,
                stage=job.stage,
                error=job.error,
            )
        )
    return ImportBatchRead(id=batch.id, state=batch.state, stage=batch.stage, error=batch.error, jobs=jobs)


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
