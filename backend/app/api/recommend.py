from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.schemas.recommend import RecommendRequest, RecommendResponse
from app.services.recommend.engine import RecommendEngine


router = APIRouter()


@router.post("/", response_model=RecommendResponse)
async def recommend_route(
    payload: RecommendRequest,
    session: Session = Depends(get_db_session),
) -> RecommendResponse:
    VisitorRepository(session).upsert(payload.session_id, payload.interests, payload.audience_type)
    return RecommendEngine(RouteRepository(session)).generate(payload)
