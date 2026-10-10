"""TTS 服务工厂与配置开关（tts_ready）的单元测试。"""

import pytest

from app.core.config import Settings
from app.services.tts import factory
from app.services.tts.bailian import BailianTTSService
from app.services.tts.volcengine import VolcengineTTSService


def _settings(**overrides) -> Settings:
    values = dict(
        tts_provider="volcengine",
        volcengine_tts_api_key="vk-test",
        volcengine_tts_voice="zh_female_zhixingnv_uranus_bigtts",
    )
    values.update(overrides)
    return Settings(**values)


# ---- Settings.tts_ready ----


def test_tts_ready_volcengine_with_api_key() -> None:
    assert _settings().tts_ready is True


def test_tts_ready_volcengine_with_app_credentials() -> None:
    settings = _settings(
        volcengine_tts_api_key="",
        volcengine_tts_app_id="app-id",
        volcengine_tts_access_key="access-key",
    )
    assert settings.tts_ready is True


def test_tts_ready_volcengine_without_credentials() -> None:
    assert _settings(volcengine_tts_api_key="").tts_ready is False


def test_tts_ready_bailian() -> None:
    assert _settings(tts_provider="bailian", tts_api_key="bk").tts_ready is True
    assert _settings(tts_provider="bailian", tts_api_key="").tts_ready is False


def test_tts_ready_stub_provider() -> None:
    assert _settings(tts_provider="stub").tts_ready is False


# ---- build_tts_service ----


def test_build_tts_service_volcengine_resolves_preset() -> None:
    service = factory.build_tts_service(_settings(), preset="gentle-female")
    assert isinstance(service, VolcengineTTSService)
    # 音色预设优先于配置默认音色
    assert service._voice == "zh_female_cancan_uranus_bigtts"


def test_build_tts_service_volcengine_unknown_preset_uses_default() -> None:
    service = factory.build_tts_service(_settings(), preset="unknown")
    assert isinstance(service, VolcengineTTSService)
    assert service._voice == "zh_female_zhixingnv_uranus_bigtts"


def test_build_tts_service_bailian_resolves_preset() -> None:
    settings = _settings(tts_provider="bailian", tts_api_key="bk")
    service = factory.build_tts_service(settings, preset="gentle-female")
    assert isinstance(service, BailianTTSService)
    assert service.voice == "longwan_v3"


def test_build_tts_service_unconfigured_raises() -> None:
    with pytest.raises(ValueError):
        factory.build_tts_service(_settings(volcengine_tts_api_key=""))


# ---- build_streaming_tts_service ----


def test_build_streaming_tts_service_volcengine() -> None:
    service = factory.build_streaming_tts_service(_settings(), preset="gentle-female")
    assert service is not None
    # create_session 只做本地构造，不发起网络连接
    session = service.create_session()
    assert session is not None


def test_build_streaming_tts_service_unconfigured_returns_none() -> None:
    assert factory.build_streaming_tts_service(_settings(volcengine_tts_api_key="")) is None
