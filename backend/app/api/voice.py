from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.services.asr.base import BaseASRService
from app.services.asr.stub import StubASRService


router = APIRouter()


def get_asr_service(settings: Settings = Depends(get_settings)) -> BaseASRService:
    if settings.asr_provider == "bailian":
        from app.services.asr.bailian import BailianASRService

        return BailianASRService(settings=settings)
    if settings.asr_provider == "qwen":
        from app.services.asr.qwen import QwenASRService

        return QwenASRService(settings=settings)
    return StubASRService()


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    settings: Settings = Depends(get_settings),
    asr_service: BaseASRService = Depends(get_asr_service),
):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio content is required.")
    if len(content) > settings.asr_max_audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio is too large (max {settings.asr_max_audio_bytes} bytes).",
        )

    payload: bytes | str = content
    if getattr(asr_service, "requires_public_audio_url", False):
        payload = _prepare_public_audio_url(content, request, settings)

    try:
        result = await asr_service.transcribe(payload)
    finally:
        close = getattr(asr_service, "aclose", None)
        if close:
            await close()
    return {
        "text": result.text,
        "confidence": result.confidence,
        "confidence_source": result.confidence_source,
        "needs_confirmation": result.needs_confirmation,
        "duration_ms": result.duration_ms,
        "provider": result.provider,
        "error_message": result.error_message,
        "candidates": [
            {"text": c.text, "confidence": c.confidence} for c in result.candidates
        ],
    }


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
