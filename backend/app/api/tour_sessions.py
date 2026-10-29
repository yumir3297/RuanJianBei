from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.tour_session import TourIdentity
from app.repositories.tour_session import IdempotencyConflict, RevisionConflict, TourSessionRepository
from app.schemas.tour_session import CreateTourSessionRequest, SaveTourSessionRequest
from app.services.tour_session_identity import ensure_tour_identity, require_tour_write_protection

router = APIRouter()


async def get_tour_identity(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> TourIdentity:
    identity, csrf = await ensure_tour_identity(request, response, db, settings.admin_token_secret)
    request.state.tour_csrf = csrf
    return identity


def _protect_write(request: Request, identity: TourIdentity, settings: Settings) -> None:
    require_tour_write_protection(request, identity, settings.admin_token_secret)


def _conflict(error: RevisionConflict) -> HTTPException:
    return HTTPException(status_code=409, detail={
        "message": str(error), "current_version": error.current_version,
    })


@router.get("/bootstrap")
async def bootstrap_tour_identity(request: Request, identity: TourIdentity = Depends(get_tour_identity)):
    return {"identity_id": identity.id, "csrf_token": request.state.tour_csrf}


@router.get("/trash")
async def list_tour_trash(
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    return {"items": await TourSessionRepository(db).list_trash(identity.id)}


@router.get("")
async def list_tour_sessions(
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    return {"items": await TourSessionRepository(db).list_sessions(identity.id)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tour_session(
    payload: CreateTourSessionRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        return await TourSessionRepository(db).create_session(
            identity.id, settings.site_id, payload.title, payload.snapshot.model_dump(), idempotency_key,
        )
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{session_id}/revisions")
async def list_tour_revisions(
    session_id: str,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    if await TourSessionRepository(db).get_session(identity.id, session_id) is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return {"items": await TourSessionRepository(db).list_revisions(identity.id, session_id)}


@router.get("/{session_id}")
async def get_tour_session(
    session_id: str,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    item = await TourSessionRepository(db).get_session(identity.id, session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return item


@router.put("/{session_id}")
async def save_tour_session(
    session_id: str,
    payload: SaveTourSessionRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        item = await TourSessionRepository(db).save_revision(
            identity.id, session_id, payload.expected_version, payload.snapshot.model_dump(), idempotency_key,
        )
    except RevisionConflict as error:
        raise _conflict(error) from error
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return item


@router.post("/{session_id}/restore/{revision_id}")
async def restore_tour_revision(
    session_id: str,
    revision_id: str,
    expected_version: Annotated[int, Query(ge=1)],
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        item = await TourSessionRepository(db).restore_revision(
            identity.id, session_id, revision_id, expected_version, idempotency_key,
        )
    except RevisionConflict as error:
        raise _conflict(error) from error
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="游览或历史版本不存在")
    return item


@router.delete("/{session_id}")
async def delete_tour_session(
    session_id: str,
    request: Request,
    expected_version: Annotated[int, Query(ge=1)],
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        item = await TourSessionRepository(db).delete_session(identity.id, session_id, expected_version)
    except RevisionConflict as error:
        raise _conflict(error) from error
    if item is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return item


@router.post("/{session_id}/undelete")
async def undelete_tour_session(
    session_id: str,
    request: Request,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    item = await TourSessionRepository(db).undelete_session(identity.id, session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="游览已过期或不存在")
    return item


@router.delete("/{session_id}/purge")
async def purge_tour_session(
    session_id: str,
    request: Request,
    confirm: bool = Query(default=False),
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    if not confirm:
        raise HTTPException(status_code=400, detail="永久删除需明确确认")
    if not await TourSessionRepository(db).purge_session(identity.id, session_id):
        raise HTTPException(status_code=404, detail="回收站中的游览不存在")
    return {"deleted": True}
