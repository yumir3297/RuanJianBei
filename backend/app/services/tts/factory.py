"""TTS 服务工厂：按配置在火山豆包 / 百炼之间分发构建，屏蔽 provider 差异。

调用方（chat.py / admin.py / welcome_cache.py）只关心「给我一个可用的 TTS 服务」，
provider 选择、凭据组装、音色解析全部收敛在这里。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import Settings
from app.services.tts.base import BaseTTSService
from app.services.tts.voices import resolve_tts_voice

if TYPE_CHECKING:  # pragma: no cover
    from app.services.tts.streaming import StreamingTTSService
    from app.services.tts.volcengine import VolcengineStreamingTTSService


def _default_voice(settings: Settings) -> str:
    if settings.tts_provider == "volcengine":
        return settings.volcengine_tts_voice
    return settings.tts_voice


def resolve_voice_for_provider(settings: Settings, preset: str | None) -> str:
    """按 provider 选择对应音色预设表，把 preset 解析为最终音色 ID。"""
    return resolve_tts_voice(preset, _default_voice(settings), provider=settings.tts_provider)


def build_tts_service(settings: Settings, preset: str | None = None) -> BaseTTSService:
    """构建非流式 TTS 服务；provider 未配置凭据时抛出 ValueError。"""
    if settings.tts_provider == "volcengine":
        from app.services.tts.volcengine import VolcengineTTSService

        if not settings.volcengine_tts_ready:
            raise ValueError("火山 TTS 凭据未配置（需要 VOLCENGINE_TTS_API_KEY 或 APP ID + Access Key）")
        return VolcengineTTSService(
            app_id=settings.volcengine_tts_app_id or None,
            access_key=settings.volcengine_tts_access_key or None,
            api_key=settings.volcengine_tts_api_key or None,
            resource_id=settings.volcengine_tts_resource_id,
            voice=resolve_voice_for_provider(settings, preset),
            format=settings.volcengine_tts_format,
            sample_rate=settings.volcengine_tts_sample_rate,
        )
    if settings.tts_provider == "bailian":
        from app.services.tts.bailian import BailianTTSService

        if not settings.tts_api_key:
            raise ValueError("百炼 TTS 凭据未配置")
        return BailianTTSService(
            api_key=settings.tts_api_key,
            base_url=settings.tts_base_url,
            model=settings.tts_model,
            voice=resolve_voice_for_provider(settings, preset),
            timeout_seconds=settings.tts_timeout_seconds,
            use_compatible_api=False,
        )
    raise ValueError(f"不支持的 TTS provider: {settings.tts_provider}")


def build_streaming_tts_service(
    settings: Settings,
    preset: str | None = None,
) -> "VolcengineStreamingTTSService | StreamingTTSService | None":
    """构建流式 TTS 服务工厂；provider 不支持或凭据缺失时返回 None（管线自动降级）。"""
    if settings.tts_provider == "volcengine":
        if not settings.volcengine_tts_ready:
            return None
        from app.services.tts.volcengine import VolcengineStreamingTTSService

        return VolcengineStreamingTTSService(
            app_id=settings.volcengine_tts_app_id or None,
            access_key=settings.volcengine_tts_access_key or None,
            api_key=settings.volcengine_tts_api_key or None,
            resource_id=settings.volcengine_tts_resource_id,
            voice=resolve_voice_for_provider(settings, preset),
            format=settings.volcengine_tts_format,
            sample_rate=settings.volcengine_tts_sample_rate,
            enable_subtitle=True,
        )
    if settings.tts_provider == "bailian" and settings.tts_api_key:
        from app.services.tts.streaming import StreamingTTSService

        return StreamingTTSService(
            api_key=settings.tts_api_key,
            model=settings.tts_model,
            voice=resolve_voice_for_provider(settings, preset),
            enable_word_timestamp=True,
        )
    return None
