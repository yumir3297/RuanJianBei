from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from app.api.router import api_router
from app.api.chat import close_cached_llm_service
from app.api.vision import close_cached_vision_service
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.bootstrap import bootstrap_avatar_configs, bootstrap_experience_demo_feedback, bootstrap_quick_topics, bootstrap_sample_data, ensure_schema_compatibility
from app.db.session import SessionLocal, engine
from app.models import (  # noqa: F401
    AvatarConfig,
    BehaviorSummary,
    ChatLog,
    FAQEntryRecord,
    KnowledgeChunk,
    KnowledgeEntry,
    KnowledgeBlindSpot,
    QACacheEntry,
    QuickTopic,
    RouteTemplate,
    VisitorProfile,
    VisitorFeedback,
)
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ui_asset_upload_root.mkdir(parents=True, exist_ok=True)
    settings.ui_asset_manifest_file.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    bootstrap_quick_topics()
    bootstrap_avatar_configs()
    bootstrap_sample_data()
    bootstrap_experience_demo_feedback()

    # 预加载模型，避免首次请求冷启动
    from app.api.chat import get_cached_embedder, get_cached_reranker
    from app.services.qa.runtime import get_runtime_faq_matcher
    from app.db.session import SessionLocal
    # 预加载 embedder（~512MB）
    embedder = get_cached_embedder(settings.embedding_model_name, str(settings.model_cache_root))

    # 预加载 reranker（~1GB）
    get_cached_reranker(
        settings.reranker_model_name,
        str(settings.model_cache_root),
        settings.reranker_batch_size,
        settings.reranker_max_length,
    )

    # 预热 FAQ 语义索引（202条alias编码，~275ms）
    session = SessionLocal()
    try:
        faq_matcher = get_runtime_faq_matcher(session, embedder=embedder)
    finally:
        session.close()

    yield
    await close_cached_llm_service()
    await close_cached_vision_service()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    app.mount("/ui-assets", StaticFiles(directory=settings.ui_asset_upload_root, check_dir=False), name="ui-assets")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service=settings.app_name)

    @app.get("/ready")
    async def ready() -> JSONResponse:
        failures: list[str] = []
        session = SessionLocal()
        try:
            knowledge_count = session.scalar(select(func.count(KnowledgeChunk.id))) or 0
            if knowledge_count == 0:
                failures.append("knowledge_chunks_empty")
        except Exception:
            failures.append("database_unavailable")
        finally:
            session.close()

        for provider, key in ((settings.llm_provider, settings.llm_api_key), (settings.asr_provider, settings.asr_api_key), (settings.tts_provider, settings.tts_api_key)):
            if provider != "stub" and not key:
                failures.append(f"{provider}_api_key_missing")
        if settings.coze_enabled and (not settings.coze_run_url or not settings.coze_token):
            failures.append("coze_configuration_missing")
        if settings.competition_mode and settings.admin_password == "admin123":
            failures.append("default_admin_password")

        status_code = 200 if not failures else 503
        return JSONResponse(status_code=status_code, content={"status": "ready" if not failures else "not_ready", "failures": failures})

    return app


app = create_app()
