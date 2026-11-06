from __future__ import annotations

from hashlib import sha256
import struct

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.core.config import Settings
from app.core.deps import get_app_settings
from app.schemas.vision import VisionAnalyzeResponse
from app.api.bounded_body import read_bounded_body
from app.api.capacity import acquire_capacity
from app.services.vision import BaseVisionService, QwenVisionService, StubVisionService, VisionResult
from app.services.vision.image_headers import InvalidImage, detect_image_mime, image_dimensions
from app.services.idempotency import IdempotencyCapacityExceeded, IdempotencyConflict, idempotency_coordinator


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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> VisionAnalyzeResponse:
    content = await read_bounded_body(request, settings.vision_max_image_bytes)
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

    actual_mime = detect_image_mime(content)
    if actual_mime != mime:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="图片实际格式与所选格式不一致，请重新选择。")
    try:
        width, height = image_dimensions(content, mime)
    except InvalidImage as exc:
        if str(exc) == "animated WebP is not supported":
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="暂不支持动态 WebP，请选择静态图片。")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片文件损坏或不完整，请重新选择。")
    except (ValueError, struct.error):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片文件损坏或不完整，请重新选择。")
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片尺寸无效，请重新选择。")
    if width * height > settings.vision_max_image_pixels:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片像素过大，请压缩后重试。")

    async def execute():
        lease = acquire_capacity(request, settings, "vision")
        try:
            result = await vision_service.analyze(
                content,
                filename=filename,
                mime_type=mime,
                prompt=question,
            )
            return _to_response(result, question).model_dump()
        finally:
            lease.release()

    if idempotency_key and idempotency_key.strip():
        semantic = "\0".join((mime, filename or "", question or "")).encode("utf-8")
        fingerprint = sha256(semantic + b"\0" + content).hexdigest()
        try:
            return VisionAnalyzeResponse.model_validate(
                await idempotency_coordinator.run("vision:analyze", idempotency_key.strip(), fingerprint, execute)
            )
        except IdempotencyConflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was used for a different request.")
        except IdempotencyCapacityExceeded:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="识别请求过多，请稍后重试。")
    return _to_response(await _run_vision(content, filename, mime, question, request, settings, vision_service), question)


async def _run_vision(content, filename, mime, question, request, settings, vision_service):
    lease = acquire_capacity(request, settings, "vision")
    try:
        return await vision_service.analyze(content, filename=filename, mime_type=mime, prompt=question)
    finally:
        lease.release()


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
