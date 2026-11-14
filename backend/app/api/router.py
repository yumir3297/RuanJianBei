from fastapi import APIRouter

from app.api import admin, auth, chat, display_assets, guide, insights, itinerary, knowledge, knowledge_imports, knowledge_publications, quick_select, recommend, tool_execution, visitor_config, vision, voice, weather
from app.api import tour_sessions, guide_loop


api_router = APIRouter(prefix="/api")
api_router.include_router(itinerary.router, prefix="/itinerary", tags=["itinerary"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(tour_sessions.router, prefix="/tour-sessions", tags=["tour-sessions"])
api_router.include_router(tool_execution.router, tags=["tool-executions"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(knowledge_publications.router, prefix="/knowledge-publications", tags=["knowledge-publications"])
api_router.include_router(knowledge_imports.router, prefix="/knowledge-imports", tags=["knowledge-imports"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
api_router.include_router(quick_select.router, prefix="/quick-select", tags=["quick-select"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(guide_loop.router, prefix="/admin/guide-loop", tags=["guide-loop-pilot"])
api_router.include_router(display_assets.router, prefix="/display-assets", tags=["display-assets"])
api_router.include_router(visitor_config.router, tags=["visitor-config"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(voice.router, prefix="/asr", tags=["asr"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(guide.router, prefix="/guide", tags=["guide"])
