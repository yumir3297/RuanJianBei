from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.repositories.guide_loop import GuideLoopRepository
from app.schemas.guide_loop import GuideLoopCaseRead, ObservationCreate, ObservationRead
from app.schemas.chat import ChatRequest


def require_guide_loop_enabled(settings: Settings = Depends(get_app_settings)) -> None:
    if not settings.guide_loop_pilot_enabled or settings.app_env.strip().lower() not in {"development", "test"}:
        raise HTTPException(status_code=404, detail="GuideLoop pilot is disabled")


router = APIRouter(dependencies=[Depends(require_admin_token), Depends(require_guide_loop_enabled)])


@router.post("/replay")
async def replay_visitor_stream(
    payload: "ChatRequest", request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    # Reuse the actual visitor pipeline behind an admin-authenticated endpoint;
    # do not expose the anonymous tourist API on the admin site.
    if payload.guide_loop is None or not payload.text_only:
        raise HTTPException(status_code=422, detail="GuideLoop context and text-only replay are required")
    from app.api.chat import _stream_chat
    return await _stream_chat(payload, request, session, settings)


@router.post("/observations", response_model=ObservationRead, status_code=status.HTTP_201_CREATED)
async def create_observation(payload: ObservationCreate, session: AsyncSession = Depends(get_db_session)):
    repository = GuideLoopRepository(session)
    try:
        observation, duplicate = await repository.record(payload)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    body = ObservationRead(
        event_id=observation.event_id,
        cluster_id=observation.cluster_id,
        requested_cluster_id=observation.requested_cluster_id or observation.cluster_id,
        replay_id=observation.replay_id,
        clarification_required=observation.match_decision == "clarify",
        reason_code=observation.reason_code,
        duplicate=duplicate,
    )
    if duplicate:
        return JSONResponse(status_code=status.HTTP_200_OK, content=body.model_dump())
    return body


@router.get("/cases", response_model=list[GuideLoopCaseRead])
async def list_cases(session: AsyncSession = Depends(get_db_session)):
    repository = GuideLoopRepository(session)
    cases = await repository.list_cases()
    await session.commit()
    return cases

from app.models.guide_loop import GuideLoopCheck
from app.schemas.guide_loop import DraftRequest, VerifyRequest, PublishRequest, ConfirmLiveRequest
from app.services.guide_loop.publication import GuideLoopPublicationService


@router.post("/cases/{case_id}/draft")
async def create_draft(case_id: str, payload: DraftRequest, session: AsyncSession = Depends(get_db_session)):
    service = GuideLoopPublicationService(session)
    try:
        case = await service.create_draft(case_id, payload)
        await session.commit()
        return {"case_id":case_id,"draft_id":case.draft_id,"draft_hash":case.draft_hash,"status":case.status}
    except LookupError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/cases/{case_id}/verify")
async def verify_draft(case_id: str, payload: VerifyRequest, session: AsyncSession = Depends(get_db_session)):
    try:
        result = await GuideLoopPublicationService(session).verify(case_id, payload.draft_id)
        await session.commit()
        return result
    except LookupError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cases/{case_id}/publish")
async def publish_draft(case_id: str, payload: PublishRequest, session: AsyncSession = Depends(get_db_session)):
    try:
        revision = await GuideLoopPublicationService(session).publish(case_id, payload.draft_id, payload.base_revision, source_reviewed=payload.source_reviewed)
        await session.commit()
        return {"case_id":case_id,"revision_id":revision.revision_id,"base_revision":revision.base_revision,"status":"published_pending_check","action":revision.action,"effective_from":revision.effective_from.isoformat(),"effective_until":revision.effective_until.isoformat() if revision.effective_until else None,"evidence_id":revision.evidence_id,"source_ref":revision.source_ref,"source_reviewed":revision.source_reviewed,"source_reviewed_at":revision.source_reviewed_at.isoformat() if revision.source_reviewed_at else None}
    except LookupError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/confirm-live")
async def confirm_live(payload: ConfirmLiveRequest, session: AsyncSession = Depends(get_db_session)):
    try:
        case = await GuideLoopPublicationService(session).confirm_live(payload.check_id, passed=payload.passed)
        await session.commit()
        check = await session.get(GuideLoopCheck, payload.check_id)
        return {"case_id":case.cluster_id,"status":case.status,"operator_passed":check.operator_passed,"operator_confirmed_at":check.operator_confirmed_at.isoformat() if check.operator_confirmed_at else None}
    except LookupError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
