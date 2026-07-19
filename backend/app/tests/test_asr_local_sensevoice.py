import asyncio
from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.asr.local_sensevoice import LocalSenseVoiceASRService


MODEL_DIR = Path("D:/A5ScenicGuideModels/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")


def test_local_sensevoice_unwraps_nested_json_text() -> None:
    transcript = "\u4f60\u597d\uff0c\u8bf7\u4e3a\u6211\u63a8\u8350\u4e00\u6761\u8def\u7ebf\uff0c\u4e0d\u8981\u592a\u70ed\u3002"
    wrapped = {
        "text": (
            '{"lang":"<|zh|>","emotion":"<|NEUTRAL|>",'
            '"event":"<|Speech|>","text":"' + transcript + '"}'
        )
    }

    result = LocalSenseVoiceASRService._unwrap_result(wrapped)

    assert result["text"] == transcript
    assert result["emotion"] == "<|NEUTRAL|>"
    assert result["event"] == "<|Speech|>"


def test_local_sensevoice_rejects_webm_without_hidden_decoder_dependency() -> None:
    service = LocalSenseVoiceASRService(Settings(asr_local_model_dir=str(MODEL_DIR)))

    result = asyncio.run(service.transcribe(b"not-a-wav"))

    assert result.provider == "local_sensevoice_unavailable"
    assert "PCM WAV" in result.error_message
    assert result.emotion_source == "unavailable"


@pytest.mark.skipif(not (MODEL_DIR / "test_wavs/zh.wav").is_file(), reason="local SenseVoice model is absent")
def test_local_sensevoice_returns_transcript_emotion_and_event() -> None:
    service = LocalSenseVoiceASRService(Settings(asr_local_model_dir=str(MODEL_DIR)))
    content = (MODEL_DIR / "test_wavs/zh.wav").read_bytes()

    result = asyncio.run(service.transcribe(content))

    assert "开放时间" in result.text
    assert result.provider == "local_sensevoice"
    assert result.emotion == "neutral"
    assert result.emotion_source == "sensevoice"
    assert result.audio_event == "speech"
