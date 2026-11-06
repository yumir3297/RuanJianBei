from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tour_sessions import _protect_write, get_tour_identity
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.tour_session import TourIdentity, TourSession
from app.repositories.tool_execution import IdempotencyConflict, JobCommandError, ToolExecutionRepository
from app.schemas.tool_execution import ToolRetryRequest

router = APIRouter()


async def _require_session(identity: TourIdentity, session_id: str, db: AsyncSession, site_id: str) -> None:
    item = await db.scalar(select(TourSession.id).where(
        TourSession.id == session_id, TourSession.owner_id == identity.id,
        TourSession.site_id == site_id, TourSession.deleted_at.is_(None),
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="游览不存在")


@router.get("/tour-sessions/{session_id}/executions")
async def list_executions(
    session_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    await _require_session(identity, session_id, db, settings.site_id)
    return {"items": await ToolExecutionRepository(db).list_jobs(
        "tourist", identity.id, settings.site_id, session_id, limit,
    )}


@router.get("/tour-sessions/{session_id}/executions/{job_id}")
async def get_execution(
    session_id: str,
    job_id: str,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    await _require_session(identity, session_id, db, settings.site_id)
    item = await ToolExecutionRepository(db).get_job("tourist", identity.id, settings.site_id, session_id, job_id)
    if item is None:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    return item


@router.get("/tour-sessions/{session_id}/executions/{job_id}/events")
async def get_execution_events(
    session_id: str,
    job_id: str,
    after_seq: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    await _require_session(identity, session_id, db, settings.site_id)
    page = await ToolExecutionRepository(db).list_events(
        "tourist", identity.id, settings.site_id, session_id, job_id, after_seq, limit,
    )
    if page is None:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    return page


@router.post("/tour-sessions/{session_id}/executions/{job_id}/cancel")
async def cancel_execution(
    session_id: str,
    job_id: str,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    await _require_session(identity, session_id, db, settings.site_id)
    try:
        item = await ToolExecutionRepository(db).request_cancel(
            "tourist", identity.id, settings.site_id, session_id, job_id, idempotency_key,
        )
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    return item


@router.post("/tour-sessions/{session_id}/executions/{job_id}/retry")
async def retry_execution(
    session_id: str,
    job_id: str,
    payload: ToolRetryRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    await _require_session(identity, session_id, db, settings.site_id)
    try:
        item = await ToolExecutionRepository(db).manual_retry(
            "tourist", identity.id, settings.site_id, session_id, job_id,
            idempotency_key, payload.confirm_duplicate_risk,
        )
    except (IdempotencyConflict, JobCommandError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    return item
