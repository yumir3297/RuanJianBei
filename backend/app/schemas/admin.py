from __future__ import annotations

from pydantic import BaseModel


class AdminOverview(BaseModel):
    knowledge_count: int
    chunk_count: int = 0
    chat_log_count: int
    visitor_count: int
    cache_count: int
    faq_count: int = 0
    route_count: int = 0
    behavior_summary_count: int = 0
    avg_latency_ms: float = 0


class AnalyticsItem(BaseModel):
    label: str
    value: int


class DataSyncReport(BaseModel):
    knowledge_imported: int
    chunk_imported: int = 0
    faq_imported: int
    route_imported: int
    behavior_imported: int
    duration_ms: int
    faq_reload_ms: float
    faq_index_count: int


class DataSyncResponse(BaseModel):
    message: str
    report: DataSyncReport


class RAGIndexReport(BaseModel):
    total_chunks: int
    indexed_chunks: int
    collection_name: str
    embedding_model_name: str
    duration_ms: int


class RAGIndexBuildResponse(BaseModel):
    message: str
    report: RAGIndexReport


class AvatarConfigResponse(BaseModel):
    id: int
    name: str
    model_path: str
    preview_url: str
    voice_type: str
    is_active: bool


class AvatarConfigActivateResponse(BaseModel):
    message: str
    config: AvatarConfigResponse


class AvatarVoicePreviewRequest(BaseModel):
    voice_type: str
    text: str = "您好，欢迎来到灵山胜境，我将为您提供智慧导览服务。"


class AvatarVoicePreviewResponse(BaseModel):
    voice_type: str
    provider_voice: str
    provider: str
    base64_audio: str
    audio_mime_type: str = "audio/mpeg"
    duration_ms: int


class TouristBackgroundAssetResponse(BaseModel):
    asset_url: str | None = None
    relative_path: str | None = None
    file_name: str | None = None
    updated_at: str | None = None


class DisplayAssetsResponse(BaseModel):
    tourist_background: TouristBackgroundAssetResponse
    welcome_text: str = ""


class DisplayAssetUploadResponse(BaseModel):
    message: str
    asset: TouristBackgroundAssetResponse


class WelcomeTextUpdateRequest(BaseModel):
    text: str


class WelcomeTextUpdateResponse(BaseModel):
    message: str
    welcome_text: str
