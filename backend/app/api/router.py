from fastapi import APIRouter

from app.api import admin, chat, insights, knowledge, quick_select, recommend, vision, voice


api_router = APIRouter(prefix="/api")
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
api_router.include_router(quick_select.router, prefix="/quick-select", tags=["quick-select"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(voice.router, prefix="/asr", tags=["asr"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
