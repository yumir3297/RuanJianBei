from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from hashlib import sha256
import io
import wave

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.api.bounded_body import read_bounded_body
from app.api.capacity import acquire_capacity
from app.services.asr.base import BaseASRService
from app.services.asr.stub import StubASRService
from app.services.idempotency import IdempotencyCapacityExceeded, IdempotencyConflict, idempotency_coordinator
from app.services.audio_duration import AudioProbeError, AudioProbeUnavailable, probe_audio_duration


router = APIRouter()


def get_asr_service(settings: Settings = Depends(get_settings)) -> BaseASRService:
    if settings.asr_provider == "local_sensevoice":
        from app.services.asr.local_sensevoice import LocalSenseVoiceASRService

        return LocalSenseVoiceASRService(settings=settings)
    if settings.asr_provider == "volcengine":
        from app.services.asr.volcengine import VolcengineASRService

        return VolcengineASRService(settings=settings)
    if settings.asr_provider == "bailian":
        from app.services.asr.bailian import BailianASRService

        return BailianASRService(settings=settings)
    return StubASRService()


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    settings: Settings = Depends(get_settings),
    asr_service: BaseASRService = Depends(get_asr_service),
):
    content = await read_bounded_body(request, settings.asr_max_audio_bytes)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio content is required.")
    if len(content) > settings.asr_max_audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio is too large (max {settings.asr_max_audio_bytes} bytes).",
        )

    mime = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    wav_mimes = {"audio/wav", "audio/x-wav", "audio/wave"}
    is_wav = content.startswith(b"RIFF") and content[8:12] == b"WAVE"
    if is_wav and mime not in wav_mimes | {"", "application/octet-stream"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="录音实际格式与声明格式不一致，请重新录音。")
    if is_wav or mime in wav_mimes:
        try:
            with wave.open(io.BytesIO(content), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                expected_bytes = frames * wav.getnchannels() * wav.getsampwidth()
                if not rate or not frames or len(wav.readframes(frames)) != expected_bytes:
                    raise ValueError("incomplete audio")
                if frames / rate > settings.asr_max_audio_seconds:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="录音时间过长，请缩短录音后重试。")
        except (wave.Error, EOFError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="录音文件损坏或格式不正确，请重新录音。")

    async def execute():
        lease = acquire_capacity(request, settings, "asr")
        try:
            provider_needs_audio = not (
                getattr(asr_service, "requires_public_audio_url", False)
                and not settings.asr_public_audio_base_url.strip()
            )
            if not is_wav and mime not in wav_mimes and not isinstance(asr_service, StubASRService) and provider_needs_audio:
                try:
                    duration = await probe_audio_duration(
                        content,
                        executable=settings.asr_ffprobe_path,
                        timeout_seconds=settings.asr_probe_timeout_seconds,
                    )
                except AudioProbeUnavailable:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="当前服务无法检查非 WAV 音频时长，请使用 WAV 或联系管理员。",
                    )
                except AudioProbeError:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="录音文件无法识别或不包含有效音轨，请重新录音。")
                if duration > settings.asr_max_audio_seconds:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="录音时间过长，请缩短录音后重试。")
            payload: bytes | str = content
            if getattr(asr_service, "requires_public_audio_url", False):
                payload = _prepare_public_audio_url(content, request, settings)
            result = await asr_service.transcribe(payload)
            return {
                "text": result.text,
                "confidence": result.confidence,
                "confidence_source": result.confidence_source,
                "needs_confirmation": result.needs_confirmation,
                "duration_ms": result.duration_ms,
                "provider": result.provider,
                "error_message": result.error_message,
                "emotion": result.emotion,
                "emotion_confidence": result.emotion_confidence,
                "emotion_source": result.emotion_source,
                "audio_event": result.audio_event,
                "candidates": [
                    {"text": c.text, "confidence": c.confidence} for c in result.candidates
                ],
            }
        finally:
            try:
                close = getattr(asr_service, "aclose", None)
                if close:
                    await close()
            finally:
                lease.release()

    key = request.headers.get("idempotency-key", "").strip()
    if key:
        fingerprint = sha256(mime.encode() + b"\0" + content).hexdigest()
        try:
            return await idempotency_coordinator.run("asr:transcribe", key, fingerprint, execute, lambda: _close_asr_service(asr_service))
        except IdempotencyConflict:
            await _close_asr_service(asr_service)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was used for a different request.")
        except IdempotencyCapacityExceeded:
            await _close_asr_service(asr_service)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="识别请求过多，请稍后重试。")
    return await execute()


@router.get("/files/{file_name}")
async def get_asr_audio_file(
    file_name: str,
    settings: Settings = Depends(get_settings),
):
    if file_name != Path(file_name).name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found.")
    file_path = settings.asr_upload_root / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found.")
    return FileResponse(file_path, media_type=_guess_audio_media_type(file_path))


def _prepare_public_audio_url(content: bytes, request: Request, settings: Settings) -> str | bytes:
    public_base = settings.asr_public_audio_base_url.strip().rstrip("/")
    if not public_base:
        return content

    settings.asr_upload_root.mkdir(parents=True, exist_ok=True)
    suffix = _audio_suffix(request.headers.get("content-type", ""))
    file_name = f"{uuid4().hex}{suffix}"
    file_path = settings.asr_upload_root / file_name
    file_path.write_bytes(content)
    return f"{public_base}/api/asr/files/{file_name}"


def _audio_suffix(content_type: str) -> str:
    normalized = content_type.lower()
    if "wav" in normalized:
        return ".wav"
    if "mp3" in normalized or "mpeg" in normalized:
        return ".mp3"
    if "m4a" in normalized or "mp4" in normalized:
        return ".m4a"
    return ".webm"


def _guess_audio_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(suffix, "application/octet-stream")


async def _close_asr_service(service: BaseASRService) -> None:
    close = getattr(service, "aclose", None)
    if close:
        await close()
