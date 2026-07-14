from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.avatar_config import AvatarConfig
from app.models.chat_log import ChatLog
from app.repositories.behavior_summary import BehaviorSummaryRepository
from app.repositories.chat_log import ChatLogRepository
from app.repositories.faq import FAQRepository
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.repositories.qa_cache import QACacheRepository
from app.repositories.route import RouteRepository
from app.repositories.visitor import VisitorRepository
from app.schemas.admin import (
    AdminOverview,
    AnalyticsItem,
    AvatarConfigActivateResponse,
    AvatarConfigResponse,
    DataSyncReport,
    DataSyncResponse,
    DisplayAssetsResponse,
    DisplayAssetUploadResponse,
    RAGIndexBuildResponse,
    RAGIndexReport,
    WelcomeTextUpdateRequest,
    WelcomeTextUpdateResponse,
)
from app.schemas.blind_spot import (
    BlindSpotRead,
    BlindSpotResolutionResponse,
    ResolveBlindSpotWithFAQRequest,
)
from app.services.data_import.importer import ProcessedDataImporter
from app.services.qa.runtime import get_runtime_faq_stats, reload_runtime_faq_matcher
from app.services.qa.blind_spot_resolution import BlindSpotResolutionService
from app.services.rag.embedder import SentenceTransformerEmbedder
from app.services.rag.index_builder import RAGIndexBuilder
from app.services.rag.vector_store import ChromaVectorStore
from app.services.display_assets import DisplayAssetService


router = APIRouter()

VALID_VOICE_TYPES = {"gentle-female", "calm-female", "deep-male", "lively-female"}

LEGACY_AVATAR_VOICE_MAP = {
    "female_warm": "gentle-female",
    "female_calm": "calm-female",
    "male_calm": "deep-male",
    "male_enthusiastic": "deep-male",
}


def _normalize_avatar_voice_type(value: str) -> str:
    return LEGACY_AVATAR_VOICE_MAP.get(value, value)


def _to_blind_spot_read(entry) -> BlindSpotRead:
    return BlindSpotRead(
        id=entry.id,
        normalized_query=entry.normalized_query,
        raw_query_samples=KnowledgeBlindSpotRepository.load_samples(entry.raw_query_samples_json),
        hit_count=entry.hit_count,
        status=entry.status,
        category=entry.category,
        resolution_type=entry.resolution_type,
        resolved_faq_id=entry.resolved_faq_id,
        resolved_knowledge_id=entry.resolved_knowledge_id,
        first_seen_at=entry.first_seen_at,
        last_seen_at=entry.last_seen_at,
        resolved_at=entry.resolved_at,
    )


@router.get("/overview", response_model=AdminOverview)
async def admin_overview(session: Session = Depends(get_db_session)) -> AdminOverview:
    avg_latency = session.execute(
        select(func.avg(ChatLog.latency_ms))
    ).scalar()

    return AdminOverview(
        knowledge_count=KnowledgeRepository(session).count(),
        chunk_count=KnowledgeChunkRepository(session).count(),
        chat_log_count=ChatLogRepository(session).count(),
        visitor_count=VisitorRepository(session).count(),
        cache_count=QACacheRepository(session).count(),
        faq_count=FAQRepository(session).count(),
        route_count=RouteRepository(session).count(),
        behavior_summary_count=BehaviorSummaryRepository(session).count(),
        avg_latency_ms=round(float(avg_latency or 0), 1),
    )


@router.get("/analytics", response_model=list[AnalyticsItem])
async def admin_analytics(session: Session = Depends(get_db_session)) -> list[AnalyticsItem]:
    behavior_summary = BehaviorSummaryRepository(session).get_latest()
    return [
        AnalyticsItem(label="知识条目数", value=KnowledgeRepository(session).count()),
        AnalyticsItem(label="知识切块数", value=KnowledgeChunkRepository(session).count()),
        AnalyticsItem(label="FAQ条目数", value=FAQRepository(session).count()),
        AnalyticsItem(label="路线模板数", value=RouteRepository(session).count()),
        AnalyticsItem(label="问答日志数", value=ChatLogRepository(session).count()),
        AnalyticsItem(label="游客画像数", value=VisitorRepository(session).count()),
        AnalyticsItem(label="行为样本行数", value=behavior_summary.row_count if behavior_summary else 0),
    ]


@router.get("/blind-spots", response_model=list[BlindSpotRead])
async def list_blind_spots(
    status: Literal["open", "resolved"] | None = "open",
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> list[BlindSpotRead]:
    entries = KnowledgeBlindSpotRepository(session).list(status=status, limit=limit)
    return [_to_blind_spot_read(entry) for entry in entries]


@router.post("/blind-spots/{blind_spot_id}/resolve-with-faq", response_model=BlindSpotResolutionResponse)
async def resolve_blind_spot_with_faq(
    blind_spot_id: int,
    payload: ResolveBlindSpotWithFAQRequest,
    session: Session = Depends(get_db_session),
) -> BlindSpotResolutionResponse:
    blind_spot = BlindSpotResolutionService(
        KnowledgeBlindSpotRepository(session),
        FAQRepository(session),
    ).resolve_with_faq(blind_spot_id, payload)
    faq_reload_ms = reload_runtime_faq_matcher(session)
    faq_stats = get_runtime_faq_stats()
    return BlindSpotResolutionResponse(
        message="Knowledge blind spot resolved with FAQ.",
        blind_spot=_to_blind_spot_read(blind_spot),
        faq_id=payload.faq_id,
        faq_reload_ms=faq_reload_ms,
        faq_index_count=int(faq_stats["entry_count"]),
        semantic_alias_count=int(faq_stats["semantic_alias_count"]),
    )


@router.post("/sync-processed-data", response_model=DataSyncResponse)
async def sync_processed_data(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> DataSyncResponse:
    report = ProcessedDataImporter(session, settings).sync()
    faq_reload_ms = reload_runtime_faq_matcher(session)
    faq_stats = get_runtime_faq_stats()

    return DataSyncResponse(
        message="Processed data synced successfully.",
        report=DataSyncReport(
            knowledge_imported=report.knowledge_imported,
            chunk_imported=report.chunk_imported,
            faq_imported=report.faq_imported,
            route_imported=report.route_imported,
            behavior_imported=report.behavior_imported,
            duration_ms=report.duration_ms,
            faq_reload_ms=faq_reload_ms,
            faq_index_count=int(faq_stats["entry_count"]),
        ),
    )


@router.post("/build-rag-index", response_model=RAGIndexBuildResponse)
async def build_rag_index(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> RAGIndexBuildResponse:
    report = RAGIndexBuilder(
        KnowledgeChunkRepository(session),
        SentenceTransformerEmbedder(settings.embedding_model_name, cache_dir=settings.model_cache_root),
        ChromaVectorStore(settings.chroma_persist_root, settings.rag_collection_name),
        batch_size=settings.rag_index_batch_size,
    ).build()

    return RAGIndexBuildResponse(
        message="RAG index built successfully.",
        report=RAGIndexReport(
            total_chunks=report.total_chunks,
            indexed_chunks=report.indexed_chunks,
            collection_name=report.collection_name,
            embedding_model_name=report.embedding_model_name,
            duration_ms=report.duration_ms,
        ),
    )


def _to_avatar_config_response(config: AvatarConfig) -> AvatarConfigResponse:
    return AvatarConfigResponse(
        id=config.id,
        name=config.name,
        model_path=config.model_path,
        preview_url=config.preview_url,
        voice_type=_normalize_avatar_voice_type(config.voice_type),
        is_active=config.is_active,
    )


def _get_display_asset_service(settings: Settings) -> DisplayAssetService:
    return DisplayAssetService(settings)


def _to_display_assets_response(service: DisplayAssetService) -> DisplayAssetsResponse:
    assets = service.get_assets()
    return DisplayAssetsResponse(
        tourist_background=assets["tourist_background"],
        welcome_text=assets["welcome_text"],
    )


@router.get("/avatar-configs", response_model=list[AvatarConfigResponse])
async def list_avatar_configs(session: Session = Depends(get_db_session)) -> list[AvatarConfigResponse]:
    configs = session.query(AvatarConfig).order_by(AvatarConfig.id).all()
    return [_to_avatar_config_response(c) for c in configs]


@router.get("/avatar-configs/active", response_model=AvatarConfigResponse)
async def get_active_avatar_config(session: Session = Depends(get_db_session)) -> AvatarConfigResponse:
    config = session.query(AvatarConfig).filter(AvatarConfig.is_active.is_(True)).first()
    if config is None:
        config = session.query(AvatarConfig).order_by(AvatarConfig.id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No avatar config found.")
    return _to_avatar_config_response(config)


@router.get("/display-assets", response_model=DisplayAssetsResponse)
async def get_display_assets(
    settings: Settings = Depends(get_app_settings),
) -> DisplayAssetsResponse:
    return _to_display_assets_response(_get_display_asset_service(settings))


@router.post("/display-assets/tourist-background", response_model=DisplayAssetUploadResponse)
async def upload_tourist_background(
    image: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
) -> DisplayAssetUploadResponse:
    service = _get_display_asset_service(settings)
    asset = await service.save_tourist_background(image)
    return DisplayAssetUploadResponse(message="Tourist background updated.", asset=asset)


@router.delete("/display-assets/tourist-background", response_model=DisplayAssetUploadResponse)
async def clear_tourist_background(
    settings: Settings = Depends(get_app_settings),
) -> DisplayAssetUploadResponse:
    service = _get_display_asset_service(settings)
    asset = service.clear_tourist_background()
    return DisplayAssetUploadResponse(message="Tourist background cleared.", asset=asset)


@router.put("/display-assets/welcome-text", response_model=WelcomeTextUpdateResponse)
async def update_welcome_text(
    payload: WelcomeTextUpdateRequest,
    settings: Settings = Depends(get_app_settings),
) -> WelcomeTextUpdateResponse:
    service = _get_display_asset_service(settings)
    text = service.update_welcome_text(payload.text)
    return WelcomeTextUpdateResponse(message="Welcome text updated.", welcome_text=text)


@router.put("/avatar-configs/{config_id}", response_model=AvatarConfigResponse)
async def update_avatar_config(
    config_id: int,
    voice_type: str = Body(..., embed=True),
    session: Session = Depends(get_db_session),
) -> AvatarConfigResponse:
    if voice_type not in VALID_VOICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不支持的音色类型: {voice_type}。仅允许: {', '.join(sorted(VALID_VOICE_TYPES))}",
        )
    config = session.query(AvatarConfig).filter(AvatarConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar config not found.")
    config.voice_type = voice_type
    session.commit()
    session.refresh(config)
    return _to_avatar_config_response(config)


@router.put("/avatar-configs/{config_id}/activate", response_model=AvatarConfigActivateResponse)
async def activate_avatar_config(
    config_id: int,
    session: Session = Depends(get_db_session),
) -> AvatarConfigActivateResponse:
    config = session.query(AvatarConfig).filter(AvatarConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar config not found.")

    session.query(AvatarConfig).filter(AvatarConfig.is_active.is_(True)).update({"is_active": False})
    config.is_active = True
    session.commit()
    session.refresh(config)

    return AvatarConfigActivateResponse(
        message=f"Avatar config '{config.name}' activated.",
        config=_to_avatar_config_response(config),
    )
