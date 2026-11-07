from __future__ import annotations

import asyncio
import gzip
import io
import json
import logging
import struct
import tempfile
import time
import uuid
import wave
from pathlib import Path
from typing import Any

import websockets

from app.core.config import Settings
from app.services.asr.base import ASRResult, BaseASRService


logger = logging.getLogger(__name__)

DEFAULT_WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
DEFAULT_RESOURCE_ID = "volc.seedasr.sauc.duration"
SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2
_AUDIO_PACKET_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH // 5  # 200 ms

_MESSAGE_FULL_CLIENT_REQUEST = 0b0001
_MESSAGE_AUDIO_ONLY_REQUEST = 0b0010
_MESSAGE_FULL_SERVER_RESPONSE = 0b1001
_MESSAGE_ERROR = 0b1111
_SERIALIZATION_NONE = 0b0000
_SERIALIZATION_JSON = 0b0001
_COMPRESSION_NONE = 0b0000
_COMPRESSION_GZIP = 0b0001
_FLAG_LAST_PACKET = 0b0010
_FLAG_HAS_SEQUENCE = 0b0001


class AudioConversionUnavailable(Exception):
    pass


class VolcengineASRService(BaseASRService):
    """Volcengine Doubao ASR streaming-input service for complete recordings.

    The browser can keep uploading its WAV body to the existing HTTP endpoint;
    this service resamples it to the required 16 kHz mono PCM WAV and streams
    the file to Volcengine over WebSocket. No public audio URL is required.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        app_id: str | None = None,
        access_key: str | None = None,
    ) -> None:
        self.settings = settings
        # The same new-console key can be reused only when it is authorized for
        # the ASR resource. A dedicated ASR key takes precedence when supplied.
        self._api_key = (
            api_key
            or settings.volcengine_asr_api_key.strip()
            or settings.volcengine_tts_api_key.strip()
        )
        self._app_id = (
            app_id
            or settings.volcengine_asr_app_id.strip()
            or settings.volcengine_tts_app_id.strip()
        )
        self._access_key = (
            access_key
            or settings.volcengine_asr_access_key.strip()
            or settings.volcengine_tts_access_key.strip()
        )

    async def transcribe(self, content: bytes | str) -> ASRResult:
        started_at = time.perf_counter()
        if not self._is_configured():
            return self._unavailable("火山 ASR 配置不完整。", started_at)
        if not isinstance(content, bytes) or not content:
            return self._unavailable("火山 ASR 需要非空音频数据。", started_at)

        try:
            audio = await self._normalize_audio(content)
            async with asyncio.timeout(self.settings.asr_timeout_seconds):
                text = await self._recognize(audio)
        except AudioConversionUnavailable:
            return self._unavailable(
                "音频需要转换为 16 kHz 单声道 WAV；请安装 FFmpeg 或检查 ASR_FFMPEG_PATH。",
                started_at,
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("Volcengine ASR timed out.")
            return self._unavailable("火山 ASR 请求超时。", started_at, error_type="Timeout")
        except Exception as exc:
            logger.warning("Volcengine ASR failed with %s.", type(exc).__name__)
            return self._unavailable(
                "火山 ASR 暂时不可用。",
                started_at,
                error_type=type(exc).__name__,
            )

        return ASRResult(
            text=text,
            confidence=0.78 if text else 0.0,
            duration_ms=self._elapsed_ms(started_at),
            provider="volcengine",
            confidence_source="heuristic" if text else "unavailable",
        )

    def _is_configured(self) -> bool:
        has_api_key = bool(self._api_key)
        has_legacy_auth = bool(self._app_id and self._access_key)
        return bool(
            (has_api_key or has_legacy_auth)
            and self.settings.volcengine_asr_resource_id.strip()
            and self.settings.volcengine_asr_ws_url.strip()
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "X-Api-Resource-Id": self.settings.volcengine_asr_resource_id.strip(),
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        else:
            headers["X-Api-App-Key"] = self._app_id
            headers["X-Api-Access-Key"] = self._access_key
        return headers

    async def _normalize_audio(self, content: bytes) -> bytes:
        try:
            with wave.open(io.BytesIO(content), "rb") as audio:
                is_supported_wav = (
                    audio.getcomptype() == "NONE"
                    and audio.getframerate() == SAMPLE_RATE
                    and audio.getnchannels() == CHANNELS
                    and audio.getsampwidth() == SAMPLE_WIDTH
                )
            if is_supported_wav:
                return content
        except (EOFError, wave.Error):
            pass
        return await self._transcode_to_supported_wav(content)

    async def _transcode_to_supported_wav(self, content: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(
            prefix="asr-normalized-",
            suffix=".wav",
            delete=False,
        ) as output:
            output_path = Path(output.name)
        try:
            try:
                process = await asyncio.create_subprocess_exec(
                    self.settings.asr_ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-protocol_whitelist",
                    "pipe",
                    "-i",
                    "pipe:0",
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-ac",
                    str(CHANNELS),
                    "-ar",
                    str(SAMPLE_RATE),
                    "-sample_fmt",
                    "s16",
                    "-c:a",
                    "pcm_s16le",
                    "-f",
                    "wav",
                    str(output_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except OSError as exc:
                raise AudioConversionUnavailable from exc

            try:
                await asyncio.wait_for(
                    process.communicate(input=content),
                    timeout=self.settings.asr_transcode_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                process.kill()
                await process.wait()
                raise AudioConversionUnavailable from exc
            except BaseException:
                process.kill()
                await process.wait()
                raise

            if process.returncode != 0:
                raise AudioConversionUnavailable
            converted = await asyncio.to_thread(output_path.read_bytes)
            try:
                with wave.open(io.BytesIO(converted), "rb") as audio:
                    frames = audio.getnframes()
                    pcm = audio.readframes(frames)
                    if (
                        audio.getcomptype() != "NONE"
                        or audio.getframerate() != SAMPLE_RATE
                        or audio.getnchannels() != CHANNELS
                        or audio.getsampwidth() != SAMPLE_WIDTH
                        or frames <= 0
                        or len(pcm) != frames * CHANNELS * SAMPLE_WIDTH
                    ):
                        raise AudioConversionUnavailable
            except (EOFError, wave.Error) as exc:
                raise AudioConversionUnavailable from exc
            return converted
        finally:
            output_path.unlink(missing_ok=True)

    async def _recognize(self, audio: bytes) -> str:
        connection = await websockets.connect(
            self.settings.volcengine_asr_ws_url.strip(),
            additional_headers=self._build_headers(),
            open_timeout=min(10.0, self.settings.asr_timeout_seconds),
            close_timeout=5.0,
            ping_interval=20.0,
            ping_timeout=10.0,
            max_size=4 * 1024 * 1024,
        )
        try:
            await connection.send(build_full_request_frame(self.settings.volcengine_asr_language))
            chunks = list(iter_audio_chunks(audio))
            for index, chunk in enumerate(chunks):
                await connection.send(
                    build_audio_frame(chunk, is_last=index == len(chunks) - 1)
                )
                if (
                    index < len(chunks) - 1
                    and self.settings.volcengine_asr_packet_interval_seconds > 0
                ):
                    await asyncio.sleep(self.settings.volcengine_asr_packet_interval_seconds)
            return await self._read_result(connection)
        finally:
            await connection.close()

    async def _read_result(self, connection: Any) -> str:
        latest_text = ""
        while True:
            message = await connection.recv()
            if isinstance(message, str):
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    latest_text = extract_result_text(payload) or latest_text
                continue

            response = parse_server_frame(bytes(message))
            if response["message_type"] == _MESSAGE_ERROR:
                raise RuntimeError("Volcengine ASR protocol error.")

            payload = response["payload"]
            if isinstance(payload, dict):
                code = payload.get("code")
                if code is not None and str(code) not in {"20000000", "20000001", "20000002"}:
                    raise RuntimeError("Volcengine ASR returned an error code.")
                latest_text = extract_result_text(payload) or latest_text
            if response["is_final"]:
                return latest_text

    def _unavailable(
        self,
        message: str,
        started_at: float,
        *,
        error_type: str | None = None,
    ) -> ASRResult:
        return ASRResult(
            text="",
            confidence=0.0,
            duration_ms=self._elapsed_ms(started_at),
            provider="volcengine_unavailable",
            confidence_source="unavailable",
            error_message=f"{message} ({error_type})" if error_type else message,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)


def _build_frame(
    message_type: int,
    flags: int,
    serialization: int,
    compression: int,
    payload: bytes,
) -> bytes:
    header = bytes(
        (
            0b0001_0001,
            (message_type << 4) | flags,
            (serialization << 4) | compression,
            0,
        )
    )
    return header + struct.pack(">I", len(payload)) + payload


def build_full_request_frame(language: str = "zh-CN") -> bytes:
    request = {
        "user": {"uid": "scenic-guide-guest"},
        "audio": {
            "format": "wav",
            "rate": SAMPLE_RATE,
            "bits": SAMPLE_WIDTH * 8,
            "channel": CHANNELS,
            "language": language,
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "show_utterances": True,
            "result_type": "full",
        },
    }
    payload = gzip.compress(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    return _build_frame(
        _MESSAGE_FULL_CLIENT_REQUEST,
        flags=0,
        serialization=_SERIALIZATION_JSON,
        compression=_COMPRESSION_GZIP,
        payload=payload,
    )


def iter_audio_chunks(audio: bytes, *, chunk_bytes: int = _AUDIO_PACKET_BYTES) -> list[bytes]:
    if not audio:
        return []
    return [audio[offset : offset + chunk_bytes] for offset in range(0, len(audio), chunk_bytes)]


def build_audio_frame(audio_chunk: bytes, *, is_last: bool) -> bytes:
    return _build_frame(
        _MESSAGE_AUDIO_ONLY_REQUEST,
        flags=_FLAG_LAST_PACKET if is_last else 0,
        serialization=_SERIALIZATION_NONE,
        compression=_COMPRESSION_GZIP,
        payload=gzip.compress(audio_chunk),
    )


def parse_server_frame(frame: bytes) -> dict[str, Any]:
    if len(frame) < 8:
        raise ValueError("Volcengine ASR response frame is too short.")
    header = frame[:4]
    header_size = (header[0] & 0x0F) * 4
    message_type = header[1] >> 4
    flags = header[1] & 0x0F
    serialization = header[2] >> 4
    compression = header[2] & 0x0F
    offset = header_size

    if message_type == _MESSAGE_ERROR:
        error_code = struct.unpack(">I", frame[offset : offset + 4])[0]
        offset += 4
        if len(frame) < offset + 4:
            return {
                "message_type": message_type,
                "flags": flags,
                "payload": {"code": error_code},
                "is_final": True,
            }

    if flags & _FLAG_HAS_SEQUENCE:
        if len(frame) < offset + 4:
            raise ValueError("Volcengine ASR response sequence is truncated.")
        offset += 4
    if len(frame) < offset + 4:
        raise ValueError("Volcengine ASR response length is missing.")
    payload_size = struct.unpack(">I", frame[offset : offset + 4])[0]
    offset += 4
    payload_bytes = frame[offset : offset + payload_size]
    if len(payload_bytes) != payload_size:
        raise ValueError("Volcengine ASR response payload is truncated.")
    if compression == _COMPRESSION_GZIP:
        payload_bytes = gzip.decompress(payload_bytes)

    payload: Any = payload_bytes
    if serialization == _SERIALIZATION_JSON:
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
    if message_type == _MESSAGE_ERROR and isinstance(payload, dict):
        payload.setdefault("code", error_code)
    return {
        "message_type": message_type,
        "flags": flags,
        "payload": payload,
        "is_final": bool(flags & _FLAG_LAST_PACKET),
    }


def extract_result_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    result = payload.get("result")
    if isinstance(result, dict):
        text = result.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        utterances = result.get("utterances")
    else:
        utterances = result if isinstance(result, list) else payload.get("utterances")
    if isinstance(utterances, list):
        parts = [
            item.get("text", "").strip()
            for item in utterances
            if isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and item["text"].strip()
        ]
        if parts:
            return "".join(parts)
    text = payload.get("text")
    return text.strip() if isinstance(text, str) else ""


__all__ = [
    "DEFAULT_RESOURCE_ID",
    "DEFAULT_WS_URL",
    "VolcengineASRService",
    "build_audio_frame",
    "build_full_request_frame",
    "extract_result_text",
    "iter_audio_chunks",
    "parse_server_frame",
]
