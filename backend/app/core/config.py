from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="A5 Scenic Guide AI")
    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./app.db")
    processed_data_dir: str = Field(default="../data/processed")
    knowledge_entries_filename: str = Field(default="knowledge_entries.json")
    guide_sections_filename: str = Field(default="guide_sections.json")
    faq_data_path: str = Field(default="../data/processed/faq_entries.json")
    faq_entries_filename: str = Field(default="faq_entries.json")
    route_recommendations_filename: str = Field(default="route_recommendations.json")
    visitor_behavior_summary_filename: str = Field(default="visitor_behavior_summary.json")
    default_knowledge_source: str = Field(default="official_data_pack")
    chroma_persist_dir: str = Field(default="../kb/chroma_db")
    model_cache_dir: str = Field(default="../.cache/huggingface")
    rag_collection_name: str = Field(default="scenic_knowledge_chunks")
    embedding_model_name: str = Field(default="BAAI/bge-small-zh-v1.5")
    faq_semantic_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    reranker_model_name: str = Field(default="BAAI/bge-reranker-base")
    reranker_batch_size: int = Field(default=8)
    reranker_max_length: int = Field(default=128)
    rag_index_batch_size: int = Field(default=32)
    rag_candidate_k: int = Field(default=5)
    rag_top_k: int = Field(default=5)
    llm_provider: str = Field(default="stub")
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_model: str = Field(default="")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=512, ge=32, le=4096)
    llm_connect_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    llm_first_token_timeout_seconds: float = Field(default=15.0, gt=0.0, le=120.0)
    llm_read_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)
    llm_total_timeout_seconds: float = Field(default=45.0, gt=0.0, le=300.0)
    llm_max_concurrency: int = Field(default=4, ge=1, le=32)
    llm_max_evidence_documents: int = Field(default=5, ge=1, le=10)
    llm_max_evidence_chars_per_document: int = Field(default=1800, ge=200, le=10000)
    vision_provider: str = Field(default="stub")
    vision_api_key: str = Field(default="")
    vision_base_url: str = Field(default="")
    vision_model: str = Field(default="")
    vision_connect_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    vision_read_timeout_seconds: float = Field(default=60.0, gt=0.0, le=120.0)
    vision_total_timeout_seconds: float = Field(default=90.0, gt=0.0, le=300.0)
    vision_max_image_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    cache_ttl_seconds: int = Field(default=7 * 24 * 60 * 60)
    enable_sample_data: bool = Field(default=True)
    default_avatar_voice: str = Field(default="female_warm")
    asr_provider: str = Field(default="stub")
    asr_api_key: str = Field(default="")
    asr_model: str = Field(default="paraformer-v2")
    asr_base_url: str = Field(default="https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription")
    asr_task_url: str = Field(default="https://dashscope.aliyuncs.com/api/v1/tasks")
    asr_vocabulary_id: str = Field(default="")
    asr_public_audio_base_url: str = Field(default="")
    asr_upload_dir: str = Field(default="../.uploads/asr")
    asr_timeout_seconds: float = Field(default=30.0, gt=0.0, le=180.0)
    asr_poll_interval_seconds: float = Field(default=0.8, gt=0.0, le=10.0)
    asr_max_audio_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    asr_hotwords: str = Field(default="灵山大佛,九龙灌浴,灵山梵宫,五印坛城,祥符禅寺,拈花堂,百子戏弥勒,阿育王柱,降魔浮雕,菩提大道,佛足坛,五智门,五明桥,五灯湖,曼飞龙塔,梵天花海,无尽意斋,香月花街,鹿鸣谷,大照壁")
    ui_asset_upload_dir: str = Field(default="../.uploads/ui-assets")
    ui_asset_manifest_path: str = Field(default="../.config/display_assets.json")
    ui_asset_max_image_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    tts_provider: str = Field(default="bailian")
    tts_api_key: str = Field(default="")
    tts_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
    )
    tts_model: str = Field(default="cosyvoice-v3-flash")
    tts_voice: str = Field(default="longwan_v3")
    tts_timeout_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
    live_data_provider: str = Field(default="mock")
    live_data_mock_weather: str = Field(default="晴")
    live_data_mock_temperature: str = Field(default="22-28°C")
    live_data_mock_crowd_level: str = Field(default="中等")
    coze_enabled: bool = Field(default=False)
    coze_run_url: str = Field(default="")
    coze_token: str = Field(default="")
    coze_timeout_seconds: float = Field(default=12.0, gt=0.0, le=60.0)
    competition_mode: bool = Field(default=False)
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://localhost:5175")
    admin_password: str = Field(default="admin123")
    admin_token_secret: str = Field(default="a5-scenic-admin-secret-key")
    admin_token_ttl_seconds: int = Field(default=8 * 60 * 60, ge=60, le=24 * 60 * 60)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def project_root(self) -> Path:
        return self.backend_root.parent

    @property
    def processed_data_root(self) -> Path:
        return (self.backend_root / self.processed_data_dir).resolve()

    @property
    def faq_file(self) -> Path:
        if self.faq_data_path:
            return (self.backend_root / self.faq_data_path).resolve()
        return self.processed_data_root / self.faq_entries_filename

    @property
    def knowledge_entries_file(self) -> Path:
        return self.processed_data_root / self.knowledge_entries_filename

    @property
    def guide_sections_file(self) -> Path:
        return self.processed_data_root / self.guide_sections_filename

    @property
    def route_recommendations_file(self) -> Path:
        return self.processed_data_root / self.route_recommendations_filename

    @property
    def visitor_behavior_summary_file(self) -> Path:
        return self.processed_data_root / self.visitor_behavior_summary_filename

    @property
    def chroma_persist_root(self) -> Path:
        return (self.backend_root / self.chroma_persist_dir).resolve()

    @property
    def model_cache_root(self) -> Path:
        return (self.backend_root / self.model_cache_dir).resolve()

    @property
    def asr_upload_root(self) -> Path:
        return (self.backend_root / self.asr_upload_dir).resolve()

    @property
    def ui_asset_upload_root(self) -> Path:
        return (self.backend_root / self.ui_asset_upload_dir).resolve()

    @property
    def ui_asset_manifest_file(self) -> Path:
        return (self.backend_root / self.ui_asset_manifest_path).resolve()

    @property
    def processed_data_available(self) -> bool:
        required_files = (
            self.knowledge_entries_file,
            self.guide_sections_file,
            self.faq_file,
            self.route_recommendations_file,
            self.visitor_behavior_summary_file,
        )
        return all(path.exists() for path in required_files)

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
