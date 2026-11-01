from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.tour_session import TourIdentity
from app.repositories.tour_session import IdempotencyConflict, RevisionConflict, TourSessionRepository
from app.repositories.tool_execution import IdempotencyConflict as ToolIdempotencyConflict, JobCommandError
from app.schemas.tool_execution import ToolPrincipal, ToolTarget
from app.services.tool_execution.commands import enqueue_registered_tool
from app.services.tool_execution.handlers import build_registry
from app.schemas.itinerary import (
    ApplyItineraryProposalRequest, CreateItineraryProposalRequest,
    SaveItineraryV2Request, StartTourRequest, UpgradeItineraryRequest, StrictModel,
    TourSnapshotV2, upgrade_snapshot,
)
from app.schemas.tour_session import CreateTourSessionRequest, SaveTourSessionRequest, TourArtifactReferenceRequest
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog, ResolvedSpot, parse_spot_reference
from app.services.itinerary.progress import ProgressCommand, ProgressConflict, TourProgress, validate_remaining_budget
from app.services.itinerary.provenance import normalize_snapshot_provenance
from app.services.itinerary.intent import snapshot_digest
from app.services.tour_session_identity import ensure_tour_identity, require_tour_write_protection

router = APIRouter()


class ProgressCommandRequest(StrictModel):
    expected_progress_version: int
    command: ProgressCommand


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


@router.get("/{session_id}/artifacts")
async def list_tour_artifacts(
    session_id: str,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    items = await TourSessionRepository(db).list_artifact_references(identity.id, session_id)
    if items is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return {"items": items}


@router.get("/{session_id}/events")
async def list_tour_events(
    session_id: str,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    items = await TourSessionRepository(db).list_events(identity.id, session_id)
    if items is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return {"items": items}


@router.post("/{session_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def add_tour_artifact(
    session_id: str,
    payload: TourArtifactReferenceRequest,
    request: Request,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    item = await TourSessionRepository(db).add_artifact_reference(
        identity.id, session_id, payload.artifact_type, payload.artifact_id, payload.revision_id,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="游览或历史版本不存在")
    return item


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
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return item


@router.put("/{session_id}/v2")
async def save_tour_session_v2(
    session_id: str, payload: SaveItineraryV2Request, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(db, site_id=settings.site_id)).list_for_site(settings.site_id)
    entries = {entry.spot_code: entry for entry in catalog.entries}
    snapshot = payload.snapshot.model_copy(deep=True)
    missing_codes = (set(snapshot.constraints.required_spots) | set(snapshot.constraints.excluded_spots)) - set(entries)
    if missing_codes:
        raise HTTPException(status_code=422, detail="必去或排除景点不在当前已发布目录中")
    for stop in snapshot.stops:
        if stop.kind != "visit" or stop.spot_code is None:
            if stop.source_entry_id or stop.source_revision_id:
                raise HTTPException(status_code=422, detail="未解析停留点不能携带已发布知识引用")
            continue
        entry = entries.get(stop.spot_code)
        if entry is None:
            raise HTTPException(status_code=422, detail=f"景点 {stop.spot_code} 不在当前已发布目录中")
        stop.source_entry_id, stop.source_revision_id = entry.entry_id, entry.published_revision_id
    current = await TourSessionRepository(db).get_session(identity.id, session_id)
    previous = TourSnapshotV2.model_validate(current["snapshot"]) if current and current["snapshot"].get("schema_version") == 2 else None
    snapshot = normalize_snapshot_provenance(snapshot, previous=previous, catalog_entries=entries)
    try:
        return await TourSessionRepository(db).save_revision(
            identity.id, session_id, payload.expected_version, snapshot.model_dump(mode="json"), idempotency_key,
            catalog_entries=entries,
        )
    except RevisionConflict as error:
        raise _conflict(error) from error
    except (IdempotencyConflict, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{session_id}/upgrade-v2")
async def upgrade_tour_session_v2(
    session_id: str, payload: UpgradeItineraryRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    repo = TourSessionRepository(db)
    current = await repo.get_session(identity.id, session_id)
    if current is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    if current["version"] != payload.expected_version:
        raise HTTPException(status_code=409, detail={"message": "行程内容已更新", "current_version": current["version"]})
    if current["snapshot"].get("schema_version") == 2:
        raise HTTPException(status_code=409, detail="行程已是 V2 格式")
    catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(db, site_id=settings.site_id)).list_for_site(settings.site_id)
    upgraded = upgrade_snapshot(current["snapshot"])
    for stop in upgraded.stops:
        parsed = parse_spot_reference(stop.name, catalog)
        if isinstance(parsed, ResolvedSpot):
            item = parsed.attraction
            stop.name, stop.spot_code = item.title, item.spot_code
            stop.source_entry_id, stop.source_revision_id = item.entry_id, item.published_revision_id
    for code_field, name_field in (("required_spots", "unresolved_required_names"),
                                   ("excluded_spots", "unresolved_excluded_names")):
        resolved, remaining = [], []
        for label in getattr(upgraded.constraints, name_field):
            parsed = parse_spot_reference(label, catalog)
            if isinstance(parsed, ResolvedSpot): resolved.append(parsed.attraction.spot_code)
            else: remaining.append(label)
        setattr(upgraded.constraints, code_field, resolved)
        setattr(upgraded.constraints, name_field, remaining)
    try:
        return await repo.save_revision(identity.id, session_id, payload.expected_version,
            upgraded.model_dump(mode="json"), idempotency_key, "upgraded", allow_upgrade=True)
    except RevisionConflict as error:
        raise _conflict(error) from error
    except (IdempotencyConflict, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{session_id}/progress")
async def get_tour_progress(session_id: str, identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session)):
    repo = TourSessionRepository(db)
    item = await repo.get_progress(identity.id, session_id)
    if item is None:
        if await repo.get_session(identity.id, session_id) is None:
            raise HTTPException(status_code=404, detail="游览不存在")
        return {"status": "not_started", "progress_version": 0, "status_by_stop": {}}
    return item


@router.post("/{session_id}/start")
async def start_tour_progress(
    session_id: str, payload: StartTourRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        result = await TourSessionRepository(db).start_progress(identity.id, session_id, payload.expected_version, idempotency_key)
    except RevisionConflict as error:
        raise _conflict(error) from error
    except (ValueError, ProgressConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return result


@router.post("/{session_id}/progress")
async def command_tour_progress(
    session_id: str, payload: ProgressCommandRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    try:
        result = await TourSessionRepository(db).command_progress(identity.id, session_id,
            payload.expected_progress_version, payload.command, idempotency_key)
    except (ValueError, ProgressConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    return result


@router.get("/{session_id}/progress/events")
async def list_tour_progress_events(session_id: str, identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session)):
    items = await TourSessionRepository(db).list_progress_events(identity.id, session_id)
    if items is None: raise HTTPException(status_code=404, detail="游览不存在")
    return {"items": items}


@router.get("/{session_id}/budget")
async def get_tour_budget(session_id: str,
        current_stop_remaining_minutes: int | None = Query(default=None, ge=0),
        identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session)):
    repo = TourSessionRepository(db)
    item = await repo.get_session(identity.id, session_id)
    if item is None: raise HTTPException(status_code=404, detail="游览不存在")
    try: snapshot = TourSnapshotV2.model_validate(item["snapshot"])
    except ValidationError as error: raise HTTPException(status_code=409, detail="请先升级到 V2 行程") from error
    raw = await repo.get_progress(identity.id, session_id)
    progress = TourProgress.model_validate(raw) if raw else None
    return validate_remaining_budget(snapshot, progress, datetime.now(UTC),
        current_stop_remaining_minutes=current_stop_remaining_minutes).model_dump(mode="json")


@router.post("/{session_id}/proposals", status_code=status.HTTP_202_ACCEPTED)
async def create_itinerary_proposal(
    session_id: str, payload: CreateItineraryProposalRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    owner_id = identity.id
    repo = TourSessionRepository(db)
    current = await repo.get_session(owner_id, session_id)
    if current is None: raise HTTPException(status_code=404, detail="游览不存在")
    if current["snapshot"].get("schema_version") != 2:
        raise HTTPException(status_code=409, detail="请先升级到 V2 行程后再创建修改提案")
    if current["version"] != payload.expected_version:
        raise HTTPException(status_code=409, detail={"message": "行程版本已变化", "current_version": current["version"]})
    if payload.draft_snapshot.schema_version != 2 or snapshot_digest(payload.draft_snapshot) != payload.draft_digest:
        raise HTTPException(status_code=422, detail="请提交摘要匹配的 V2 行程草稿")
    progress_raw = await repo.get_progress(owner_id, session_id)
    progress_version = int((progress_raw or {}).get("progress_version", 0))
    if payload.progress_version != progress_version:
        raise HTTPException(status_code=409, detail="游览进度已变化，请刷新后重试")
    catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(db, site_id=settings.site_id)).list_for_site(settings.site_id)
    entries = {entry.spot_code: entry for entry in catalog.entries}
    previous = TourSnapshotV2.model_validate(current["snapshot"])
    sanitized_draft = normalize_snapshot_provenance(
        payload.draft_snapshot, previous=previous, catalog_entries=entries,
    )
    draft_json = sanitized_draft.model_dump(mode="json")
    try:
        reservation, owns_execution = await repo.reserve_proposal(
            owner_id, session_id, payload.expected_version, payload.progress_version,
            payload.draft_digest, catalog.digest, payload.text,
            draft_json, idempotency_key, commit=False,
        )
        if not owns_execution:
            await db.rollback()
            existing = await repo.get_proposal(owner_id, session_id, reservation["id"])
            if existing is None:
                raise HTTPException(status_code=404, detail="行程提案不存在")
            return JSONResponse(status_code=202, content=existing)

        tool_input = {
            "proposal_id": reservation["id"],
            "idempotency_key": idempotency_key,
            "request_text": payload.text,
            "draft_digest": payload.draft_digest,
            "normalized_draft_digest": snapshot_digest(sanitized_draft),
            "catalog_digest": catalog.digest,
            "draft_snapshot": draft_json,
        }
        job = await enqueue_registered_tool(
            db, build_registry(), principal=ToolPrincipal(id=owner_id),
            site_id=settings.site_id,
            target=ToolTarget(
                id=session_id, base_revision=payload.expected_version,
                progress_version=payload.progress_version, content_digest=catalog.digest,
            ),
            tool_name="itinerary.proposal", tool_version="1", workflow_schema_version="1",
            payload=tool_input, idempotency_key=idempotency_key,
            deadline_seconds=1800, commit=False,
        )
        from app.models.tour_session import ItineraryProposal

        proposal_row = await db.get(ItineraryProposal, reservation["id"])
        if proposal_row is None:
            raise JobCommandError("行程提案预留记录不存在")
        proposal_row.execution_job_id = job["id"]
        await db.commit()
    except IntegrityError:
        await db.rollback()
        try:
            existing = await repo.find_proposal_replay(
                owner_id, session_id, payload.expected_version, payload.progress_version,
                payload.draft_digest, catalog.digest, payload.text, idempotency_key,
            )
        except IdempotencyConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if existing is None:
            raise HTTPException(status_code=409, detail="提案已被其他请求创建，请刷新后重试")
        return JSONResponse(status_code=202, content=existing)
    except (IdempotencyConflict, ToolIdempotencyConflict) as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (JobCommandError, ValueError) as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    created = await repo.get_proposal(owner_id, session_id, reservation["id"])
    if created is None:
        raise HTTPException(status_code=404, detail="行程提案不存在")
    return JSONResponse(status_code=202, content=created)


@router.get("/{session_id}/proposals")
async def list_itinerary_proposals(
    session_id: str,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    identity: TourIdentity = Depends(get_tour_identity),
    db: AsyncSession = Depends(get_db_session),
):
    items = await TourSessionRepository(db).list_proposals(identity.id, session_id, limit)
    if items is None:
        raise HTTPException(status_code=404, detail="游览不存在")
    response.headers["Cache-Control"] = "no-store"
    return {"items": items}


@router.get("/{session_id}/proposals/{proposal_id}")
async def get_itinerary_proposal(session_id: str, proposal_id: str, response: Response,
        identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session)):
    item = await TourSessionRepository(db).get_proposal(identity.id, session_id, proposal_id)
    if item is None: raise HTTPException(status_code=404, detail="行程提案不存在")
    response.headers["Cache-Control"] = "no-store"
    return item


@router.post("/{session_id}/proposals/{proposal_id}/apply")
async def apply_itinerary_proposal(
    session_id: str, proposal_id: str, payload: ApplyItineraryProposalRequest, request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    identity: TourIdentity = Depends(get_tour_identity), db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    _protect_write(request, identity, settings)
    repo = TourSessionRepository(db)
    proposal = await repo.get_proposal(identity.id, session_id, proposal_id)
    if proposal is None: raise HTTPException(status_code=404, detail="行程提案不存在")
    catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(db, site_id=settings.site_id)).list_for_site(settings.site_id)
    if proposal["catalog_digest"] != catalog.digest:
        raise HTTPException(status_code=409, detail="景点资料已更新，请重新生成提案")
    try:
        result = await repo.apply_proposal(identity.id, session_id, proposal_id, payload.expected_version,
            payload.progress_version, payload.draft_digest, idempotency_key,
            catalog_entries={entry.spot_code: entry for entry in catalog.entries})
    except RevisionConflict as error:
        raise _conflict(error) from error
    except (IdempotencyConflict, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None: raise HTTPException(status_code=404, detail="行程提案不存在")
    return result


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
