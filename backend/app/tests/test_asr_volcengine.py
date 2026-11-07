from __future__ import annotations

import asyncio
import gzip
import io
import json
import shutil
import struct
import wave

import pytest

from app.core.config import Settings
from app.services.asr.volcengine import (
    DEFAULT_RESOURCE_ID,
    DEFAULT_WS_URL,
    VolcengineASRService,
    build_audio_frame,
    build_full_request_frame,
    parse_server_frame,
)


def asr_settings(**overrides) -> Settings:
    values = {
        "asr_provider": "volcengine",
        "volcengine_asr_api_key": "test-volcengine-key",
        "volcengine_asr_resource_id": DEFAULT_RESOURCE_ID,
        "volcengine_asr_ws_url": DEFAULT_WS_URL,
        "volcengine_asr_language": "zh-CN",
        "volcengine_asr_packet_interval_seconds": 0,
        "asr_timeout_seconds": 3,
    }
    values.update(overrides)
    return Settings(**values)


def wav_audio(*, sample_rate: int = 16_000, seconds: float = 0.4) -> bytes:
    output = io.BytesIO()
    frame_count = int(sample_rate * seconds)
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x01\x00" * frame_count)
    return output.getvalue()


def server_frame(payload: dict, *, flags: int = 0b0011, sequence: int = 1) -> bytes:
    encoded = gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    frame = bytearray((0b0001_0001, (0b1001 << 4) | flags, (0b0001 << 4) | 0b0001, 0))
    if flags & 0b0001:
        frame.extend(struct.pack(">i", sequence))
    frame.extend(struct.pack(">I", len(encoded)))
    frame.extend(encoded)
    return bytes(frame)


class FakeWebSocket:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = list(responses)
        self.sent: list[bytes] = []
        self.closed = False

    async def send(self, message: bytes) -> None:
        self.sent.append(bytes(message))

    async def recv(self) -> bytes:
        if not self.responses:
            raise AssertionError("Unexpected extra WebSocket receive")
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


def unpack_client_frame(frame: bytes) -> tuple[int, int, int, bytes]:
    header = frame[:4]
    message_type = header[1] >> 4
    flags = header[1] & 0x0F
    serialization = header[2] >> 4
    compression = header[2] & 0x0F
    offset = 4
    payload_size = struct.unpack(">I", frame[offset : offset + 4])[0]
    payload = frame[offset + 4 : offset + 4 + payload_size]
    if compression == 1:
        payload = gzip.decompress(payload)
    return message_type, flags, serialization, payload


def test_volcengine_asr_sends_wav_over_v3_websocket_and_parses_final_text(monkeypatch) -> None:
    fake = FakeWebSocket([server_frame({"result": {"text": "请介绍灵山大佛。"}})])
    connect_calls: list[dict] = []

    async def fake_connect(url, *, additional_headers, **kwargs):
        connect_calls.append({"url": url, "headers": additional_headers, "kwargs": kwargs})
        return fake

    monkeypatch.setattr("app.services.asr.volcengine.websockets.connect", fake_connect)

    result = asyncio.run(VolcengineASRService(asr_settings()).transcribe(wav_audio()))

    assert result.provider == "volcengine"
    assert result.text == "请介绍灵山大佛。"
    assert result.confidence_source == "heuristic"
    assert result.needs_confirmation is True
    assert connect_calls[0]["url"] == DEFAULT_WS_URL
    assert connect_calls[0]["headers"]["X-Api-Key"] == "test-volcengine-key"
    assert connect_calls[0]["headers"]["X-Api-Resource-Id"] == DEFAULT_RESOURCE_ID
    assert fake.closed is True

    message_type, flags, serialization, payload = unpack_client_frame(fake.sent[0])
    assert (message_type, flags, serialization) == (0b0001, 0, 0b0001)
    request = json.loads(payload)
    assert request["audio"] == {
        "format": "wav",
        "rate": 16_000,
        "bits": 16,
        "channel": 1,
        "language": "zh-CN",
    }
    assert request["request"]["model_name"] == "bigmodel"

    audio_frames = [unpack_client_frame(frame) for frame in fake.sent[1:]]
    assert len(audio_frames) >= 1
    assert all(frame[0] == 0b0010 for frame in audio_frames)
    assert audio_frames[-1][1] == 0b0010
    assert audio_frames[0][3].startswith(b"RIFF")
    assert b"".join(frame[3] for frame in audio_frames) == wav_audio()


def test_volcengine_asr_reuses_tts_key_only_as_backend_credential() -> None:
    service = VolcengineASRService(
        asr_settings(volcengine_asr_api_key="", volcengine_tts_api_key="shared-test-key")
    )

    assert service._is_configured() is True
    assert service._build_headers()["X-Api-Key"] == "shared-test-key"


def test_volcengine_asr_can_use_legacy_app_id_and_access_key() -> None:
    service = VolcengineASRService(
        asr_settings(
            volcengine_asr_api_key="",
            volcengine_tts_api_key="",
            volcengine_asr_app_id="test-app-id",
            volcengine_asr_access_key="test-access-key",
        )
    )

    headers = service._build_headers()
    assert headers["X-Api-App-Key"] == "test-app-id"
    assert headers["X-Api-Access-Key"] == "test-access-key"


def test_volcengine_asr_resamples_audio_when_wav_is_not_16khz_mono(monkeypatch) -> None:
    service = VolcengineASRService(asr_settings())
    converted = wav_audio(sample_rate=16_000)
    calls: list[bytes] = []

    async def fake_transcode(content: bytes) -> bytes:
        calls.append(content)
        return converted

    monkeypatch.setattr(service, "_transcode_to_supported_wav", fake_transcode)
    original = wav_audio(sample_rate=48_000)
    result = asyncio.run(service._normalize_audio(original))

    assert calls == [original]
    assert result == converted


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is an optional runtime binary")
def test_ffmpeg_transcoder_emits_a_seekable_wav_with_correct_length() -> None:
    settings = Settings(_env_file=None, asr_ffmpeg_path=shutil.which("ffmpeg") or "ffmpeg")
    service = VolcengineASRService(settings)
    original = wav_audio(sample_rate=48_000, seconds=0.1)

    converted = asyncio.run(service._normalize_audio(original))

    with wave.open(io.BytesIO(converted), "rb") as audio:
        assert audio.getframerate() == 16_000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getnframes() == 1_600
        assert len(audio.readframes(audio.getnframes())) == 3_200


def test_volcengine_asr_reuses_already_supported_wav_without_ffmpeg() -> None:
    service = VolcengineASRService(asr_settings())
    audio = wav_audio(sample_rate=16_000)

    assert asyncio.run(service._normalize_audio(audio)) == audio


def test_volcengine_asr_parses_gzipped_final_response() -> None:
    parsed = parse_server_frame(server_frame({"result": [{"text": "识别完成"}]}))

    assert parsed["message_type"] == 0b1001
    assert parsed["is_final"] is True
    assert parsed["payload"]["result"][0]["text"] == "识别完成"


def test_build_audio_frame_marks_the_last_packet() -> None:
    frame = build_audio_frame(b"audio", is_last=True)
    message_type, flags, serialization, payload = unpack_client_frame(frame)

    assert message_type == 0b0010
    assert flags == 0b0010
    assert serialization == 0
    assert payload == b"audio"


def test_build_full_request_frame_is_gzipped_json() -> None:
    frame = build_full_request_frame("zh-CN")
    message_type, flags, serialization, payload = unpack_client_frame(frame)

    assert message_type == 0b0001
    assert flags == 0
    assert serialization == 0b0001
    assert json.loads(payload)["audio"]["language"] == "zh-CN"
