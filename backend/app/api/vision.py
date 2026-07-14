from __future__ import annotations

from hashlib import sha256

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.core.config import Settings
from app.core.deps import get_app_settings
from app.schemas.vision import VisionAnalyzeResponse
from app.services.vision import BaseVisionService, QwenVisionService, StubVisionService, VisionResult


router = APIRouter()
_cached_vision_service: BaseVisionService | None = None
_cached_vision_signature: tuple | None = None

ALLOWED_VISION_MIME = frozenset({"image/jpeg", "image/png", "image/webp"})


def get_cached_vision_service(settings: Settings) -> BaseVisionService:
    global _cached_vision_service, _cached_vision_signature
    signature = (
        settings.vision_provider,
        settings.vision_base_url,
        settings.vision_model,
        sha256(settings.vision_api_key.encode("utf-8")).hexdigest()
        if settings.vision_api_key
        else "",
        settings.vision_connect_timeout_seconds,
        settings.vision_read_timeout_seconds,
        settings.vision_total_timeout_seconds,
    )
    if _cached_vision_service is not None and signature == _cached_vision_signature:
        return _cached_vision_service

    if settings.vision_provider.strip().lower() == "qwen":
        _cached_vision_service = QwenVisionService(settings)
    else:
        _cached_vision_service = StubVisionService()
    _cached_vision_signature = signature
    return _cached_vision_service


async def close_cached_vision_service() -> None:
    global _cached_vision_service, _cached_vision_signature
    if _cached_vision_service is not None:
        await _cached_vision_service.aclose()
    _cached_vision_service = None
    _cached_vision_signature = None


def get_vision_service(settings: Settings = Depends(get_app_settings)) -> BaseVisionService:
    return get_cached_vision_service(settings)


def _normalize_mime(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    parts = content_type.split(";")
    mime = parts[0].strip().lower()
    if not mime or mime == "application/octet-stream":
        return None
    return mime


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_image(
    request: Request,
    question: str | None = Query(default=None, max_length=500),
    filename: str | None = Query(default=None, max_length=200),
    content_type: str | None = Header(default=None),
    settings: Settings = Depends(get_app_settings),
    vision_service: BaseVisionService = Depends(get_vision_service),
) -> VisionAnalyzeResponse:
    content = await request.body()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image content is required.")

    mime = _normalize_mime(content_type)
    if mime is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 JPEG、PNG 或 WebP 图片。",
        )
    if mime not in ALLOWED_VISION_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 JPEG、PNG 或 WebP 图片。",
        )

    if len(content) > settings.vision_max_image_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large.")

    result = await vision_service.analyze(
        content,
        filename=filename,
        mime_type=mime,
        prompt=question,
    )
    return _to_response(result, question)


def _to_response(result: VisionResult, question: str | None) -> VisionAnalyzeResponse:
    return VisionAnalyzeResponse(
        scene_summary=result.scene_summary,
        detected_text=result.detected_text,
        candidate_attractions=list(result.candidate_attractions),
        visual_tags=list(result.visual_tags),
        query_hints=list(result.query_hints),
        retrieval_query=result.as_retrieval_query(question),
        confidence=result.confidence,
        provider=result.provider,
    )
