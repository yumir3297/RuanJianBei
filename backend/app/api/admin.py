from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
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
    AvatarVoicePreviewRequest,
    AvatarVoicePreviewResponse,
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
from app.services.tts.bailian import BailianTTSService
from app.services.tts.voices import resolve_tts_voice
from app.services.tts.welcome_cache import _derive_model_key, generate_and_cache


router = APIRouter(dependencies=[Depends(require_admin_token)])

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
async def admin_overview(session: AsyncSession = Depends(get_db_session)) -> AdminOverview:
    avg_latency = (await session.execute(
        select(func.avg(ChatLog.latency_ms)).where(ChatLog.latency_ms > 0)
    )).scalar()

    return AdminOverview(
        knowledge_count=await KnowledgeRepository(session).count(),
        chunk_count=await KnowledgeChunkRepository(session).count(),
        chat_log_count=await ChatLogRepository(session).count(),
        visitor_count=await VisitorRepository(session).count(),
        cache_count=await QACacheRepository(session).count(),
        faq_count=await FAQRepository(session).count(),
        route_count=await RouteRepository(session).count(),
        behavior_summary_count=await BehaviorSummaryRepository(session).count(),
        avg_latency_ms=round(float(avg_latency or 0), 1),
    )


@router.get("/analytics", response_model=list[AnalyticsItem])
async def admin_analytics(session: AsyncSession = Depends(get_db_session)) -> list[AnalyticsItem]:
    behavior_summary = await BehaviorSummaryRepository(session).get_latest()
    return [
        AnalyticsItem(label="知识条目数", value=await KnowledgeRepository(session).count()),
        AnalyticsItem(label="知识切块数", value=await KnowledgeChunkRepository(session).count()),
        AnalyticsItem(label="FAQ条目数", value=await FAQRepository(session).count()),
        AnalyticsItem(label="路线模板数", value=await RouteRepository(session).count()),
        AnalyticsItem(label="问答日志数", value=await ChatLogRepository(session).count()),
        AnalyticsItem(label="游客画像数", value=await VisitorRepository(session).count()),
        AnalyticsItem(label="行为样本行数", value=behavior_summary.row_count if behavior_summary else 0),
    ]


@router.get("/blind-spots", response_model=list[BlindSpotRead])
async def list_blind_spots(
    status: Literal["open", "resolved"] | None = "open",
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[BlindSpotRead]:
    entries = await KnowledgeBlindSpotRepository(session).list(status=status, limit=limit)
    return [_to_blind_spot_read(entry) for entry in entries]


@router.post("/blind-spots/{blind_spot_id}/resolve-with-faq", response_model=BlindSpotResolutionResponse)
async def resolve_blind_spot_with_faq(
    blind_spot_id: int,
    payload: ResolveBlindSpotWithFAQRequest,
    session: AsyncSession = Depends(get_db_session),
) -> BlindSpotResolutionResponse:
    blind_spot = await BlindSpotResolutionService(
        KnowledgeBlindSpotRepository(session),
        FAQRepository(session),
    ).resolve_with_faq(blind_spot_id, payload)
    faq_reload_ms = await reload_runtime_faq_matcher(session)
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
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> DataSyncResponse:
    report = await ProcessedDataImporter(session, settings).sync()
    faq_reload_ms = await reload_runtime_faq_matcher(session)
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
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> RAGIndexBuildResponse:
    report = await RAGIndexBuilder(
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
async def list_avatar_configs(session: AsyncSession = Depends(get_db_session)) -> list[AvatarConfigResponse]:
    result = await session.execute(select(AvatarConfig).order_by(AvatarConfig.id))
    configs = result.scalars().all()
    return [_to_avatar_config_response(c) for c in configs]


@router.get("/avatar-configs/active", response_model=AvatarConfigResponse)
async def get_active_avatar_config(session: AsyncSession = Depends(get_db_session)) -> AvatarConfigResponse:
    result = await session.execute(select(AvatarConfig).where(AvatarConfig.is_active.is_(True)))
    config = result.scalar_one_or_none()
    if config is None:
        result = await session.execute(select(AvatarConfig).order_by(AvatarConfig.id))
        config = result.scalar_one_or_none()
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
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> AvatarConfigResponse:
    if voice_type not in VALID_VOICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不支持的音色类型: {voice_type}。仅允许: {', '.join(sorted(VALID_VOICE_TYPES))}",
        )
    result = await session.execute(select(AvatarConfig).where(AvatarConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar config not found.")
    config.voice_type = voice_type
    await session.commit()
    await session.refresh(config)

    # 如果修改的是当前激活的角色，后台预生成欢迎语音频
    if config.is_active and settings.tts_provider == "bailian" and settings.tts_api_key:
        _schedule_welcome_audio_regeneration(config, settings)

    return _to_avatar_config_response(config)


@router.post("/avatar-voice-preview", response_model=AvatarVoicePreviewResponse)
async def preview_avatar_voice(
    payload: AvatarVoicePreviewRequest,
    settings: Settings = Depends(get_app_settings),
) -> AvatarVoicePreviewResponse:
    if payload.voice_type not in VALID_VOICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不支持的音色类型: {payload.voice_type}",
        )
    if settings.tts_provider != "bailian" or not settings.tts_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="百炼 TTS 尚未配置，当前无法进行真实音色试听。",
        )

    text = payload.text.strip()[:100]
    if not text:
        raise HTTPException(status_code=422, detail="试听文本不能为空。")
    provider_voice = resolve_tts_voice(payload.voice_type, settings.tts_voice)
    audio = await BailianTTSService(
        api_key=settings.tts_api_key,
        base_url=settings.tts_base_url,
        model=settings.tts_model,
        voice=provider_voice,
        timeout_seconds=settings.tts_timeout_seconds,
        use_compatible_api=False,
    ).synthesize(text)
    if not audio.base64_audio:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"音色 {provider_voice} 合成失败，请检查百炼音色权限或服务状态。",
        )
    return AvatarVoicePreviewResponse(
        voice_type=payload.voice_type,
        provider_voice=provider_voice,
        provider=audio.provider,
        base64_audio=audio.base64_audio,
        duration_ms=audio.duration_ms,
    )


@router.put("/avatar-configs/{config_id}/activate", response_model=AvatarConfigActivateResponse)
async def activate_avatar_config(
    config_id: int,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> AvatarConfigActivateResponse:
    result = await session.execute(select(AvatarConfig).where(AvatarConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar config not found.")

    await session.execute(update(AvatarConfig).where(AvatarConfig.is_active.is_(True)).values(is_active=False))
    config.is_active = True
    await session.commit()
    await session.refresh(config)

    # 后台预生成欢迎语音频
    if settings.tts_provider == "bailian" and settings.tts_api_key:
        _schedule_welcome_audio_regeneration(config, settings)

    return AvatarConfigActivateResponse(
        message=f"Avatar config '{config.name}' activated.",
        config=_to_avatar_config_response(config),
    )


def _schedule_welcome_audio_regeneration(config, settings: Settings):
    """Fire-and-forget background task to pre-generate welcome TTS audio."""
    model_key = _derive_model_key(config.model_path)
    asyncio.create_task(
        generate_and_cache(
            model_key=model_key,
            voice_type=config.voice_type,
            api_key=settings.tts_api_key,
            base_url=settings.tts_base_url,
            model=settings.tts_model,
            fallback_voice=settings.tts_voice,
            timeout_seconds=settings.tts_timeout_seconds,
        )
    )


@router.post("/avatar-configs/welcome-audio/regenerate")
async def regenerate_welcome_audio(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    """Pre-generate welcome TTS audio for the currently active avatar config."""
    result = await session.execute(
        select(AvatarConfig).where(AvatarConfig.is_active.is_(True))
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active avatar config found.")

    if settings.tts_provider != "bailian" or not settings.tts_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="百炼 TTS 尚未配置，无法预生成欢迎语音频。",
        )

    model_key = _derive_model_key(config.model_path)
    audio = await generate_and_cache(
        model_key=model_key,
        voice_type=config.voice_type,
        api_key=settings.tts_api_key,
        base_url=settings.tts_base_url,
        model=settings.tts_model,
        fallback_voice=settings.tts_voice,
        timeout_seconds=settings.tts_timeout_seconds,
    )

    if not audio.base64_audio:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="欢迎语音频合成失败，请检查百炼服务状态。",
        )

    return {
        "message": "Welcome audio regenerated successfully.",
        "duration_ms": audio.duration_ms,
        "provider": audio.provider,
    }
