from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.schemas.visitor_config import PublicVisitorConfig
from app.services.visitor_config import VisitorConfigService


router = APIRouter()


@router.get("/visitor-config", response_model=PublicVisitorConfig)
async def get_visitor_config(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> PublicVisitorConfig:
    response.headers["Cache-Control"] = "no-store"
    return await VisitorConfigService(session, settings).read()
