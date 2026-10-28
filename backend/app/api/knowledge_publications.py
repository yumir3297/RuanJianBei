from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.deps import get_db_session
from app.schemas.knowledge_workspace import PublicationCreate, PublicationRead
from app.services.knowledge.publication import KnowledgePublicationService

router = APIRouter(dependencies=[Depends(require_admin_token)])


def _to_read(job) -> PublicationRead:
    return PublicationRead(id=job.id, state=job.state, error=job.error)


@router.post("/", response_model=PublicationRead, status_code=status.HTTP_202_ACCEPTED)
async def create_publication(
    payload: PublicationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> PublicationRead:
    job = await KnowledgePublicationService(session).create_publication(
        payload.items,
        idempotency_key=payload.idempotency_key,
    )
    return _to_read(job)


@router.get("/{job_id}", response_model=PublicationRead)
async def get_publication(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PublicationRead:
    return _to_read(await KnowledgePublicationService(session).get_publication(job_id))


@router.post("/{job_id}/retry", response_model=PublicationRead, status_code=status.HTTP_202_ACCEPTED)
async def retry_publication(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PublicationRead:
    return _to_read(await KnowledgePublicationService(session).retry_publication(job_id))
