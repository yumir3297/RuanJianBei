from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.chat import close_cached_llm_service
from app.api.vision import close_cached_vision_service
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.bootstrap import bootstrap_avatar_configs, bootstrap_experience_demo_feedback, bootstrap_quick_topics, bootstrap_sample_data
from app.db.session import AsyncSessionLocal
from app.services.knowledge.jobs import run_import_worker, run_publication_worker
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


class SPAStaticFiles(StaticFiles):
    """Serve a built single-page app without swallowing missing API routes."""

    async def get_response(self, path: str, scope):
        normalized_path = path.replace("\\", "/").lstrip("/")
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or normalized_path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404 and not normalized_path.startswith("api/"):
            return await super().get_response("index.html", scope)
        return response


def _run_migrations() -> None:
    """使用 Alembic 执行数据库迁移，替代 create_all。"""
    alembic_ini = Path(__file__).parent / "alembic.ini"
    if not alembic_ini.exists():
        return
    os.chdir(Path(__file__).parent)
    alembic_cfg = AlembicConfig(str(alembic_ini))
    alembic_command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    security_failures = settings.production_security_failures
    if security_failures:
        raise RuntimeError(
            "Unsafe production security configuration: " + ", ".join(security_failures)
        )
    settings.ui_asset_upload_root.mkdir(parents=True, exist_ok=True)
    settings.knowledge_upload_root.mkdir(parents=True, exist_ok=True)
    settings.ui_asset_manifest_file.parent.mkdir(parents=True, exist_ok=True)
    _run_migrations()
    await bootstrap_quick_topics()
    await bootstrap_avatar_configs()
    await bootstrap_sample_data()
    await bootstrap_experience_demo_feedback()

    # 预加载模型，避免首次请求冷启动
    from app.api.chat import get_cached_embedder, get_cached_reranker
    from app.services.qa.runtime import get_runtime_faq_matcher, set_faq_semantic_index_failed
    set_faq_semantic_index_failed(False)
    # 预加载 embedder（~512MB）
    embedder = None
    try:
        embedder = get_cached_embedder(settings.embedding_model_name, str(settings.model_cache_root))
        app.state.embedding_model_available = True
    except Exception:
        app.state.embedding_model_available = False
        logging.getLogger(__name__).exception("Embedding model unavailable; starting with repository-backed retrieval.")

    # 预加载 reranker（~1GB）
    get_cached_reranker(
        settings.reranker_model_name,
        str(settings.model_cache_root),
        settings.reranker_batch_size,
        settings.reranker_max_length,
    )

    # Load exact/fuzzy FAQ first; a semantic-index failure must not prevent startup.
    async with AsyncSessionLocal() as session:
        await get_runtime_faq_matcher(session)
        if embedder is not None:
            try:
                await get_runtime_faq_matcher(session, embedder=embedder,
                                              semantic_threshold=settings.faq_semantic_threshold)
                app.state.faq_semantic_index_available = True
            except Exception:
                app.state.faq_semantic_index_available = False
                set_faq_semantic_index_failed(True)
                logging.getLogger(__name__).exception("FAQ semantic index unavailable; using exact and fuzzy matching.")

    publication_worker = asyncio.create_task(run_publication_worker(settings))
    import_worker = asyncio.create_task(run_import_worker(settings))

    yield
    publication_worker.cancel()
    import_worker.cancel()
    await asyncio.gather(publication_worker, import_worker, return_exceptions=True)
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
        if getattr(app.state, "embedding_model_available", None) is False:
            failures.append("embedding_model_unavailable")
        from app.services.qa.runtime import faq_semantic_index_failed
        if faq_semantic_index_failed():
            failures.append("faq_semantic_index_unavailable")
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(func.count(KnowledgeChunk.chunk_id)))
                knowledge_count = result.scalar_one() or 0
                if knowledge_count == 0:
                    failures.append("knowledge_chunks_empty")
            except Exception:
                failures.append("database_unavailable")

        for provider, key in ((settings.llm_provider, settings.llm_api_key), (settings.asr_provider, settings.asr_api_key), (settings.tts_provider, settings.tts_api_key)):
            if provider != "stub" and not key:
                failures.append(f"{provider}_api_key_missing")
        if settings.competition_mode and settings.admin_password == "admin123" and "default_admin_password" not in failures:
            failures.append("default_admin_password")
        failures.extend(settings.production_security_failures)

        status_code = 200 if not failures else 503
        return JSONResponse(status_code=status_code, content={"status": "ready" if not failures else "not_ready", "failures": failures})

    # In the reviewer bundle the prebuilt Vue app lives next to the backend.
    # Mount it last so API routes, health checks, and uploaded UI assets retain
    # their normal paths; Vite development remains unaffected.
    frontend_dist = settings.project_root / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
