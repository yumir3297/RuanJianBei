from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.vision import get_vision_service
from app.core.config import Settings
from app.core.deps import get_app_settings
from app.services.vision import BaseVisionService, VisionResult
from app.services.capacity import CapacityLimiter
from main import app

_IMAGES = Path(__file__).parent / "fixtures" / "images"



class FakeVisionService(BaseVisionService):
    async def analyze(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionResult:
        assert content == (_IMAGES / "tiny.jpg").read_bytes()
        assert filename == "lingshan.jpg"
        assert mime_type == "image/jpeg"
        assert prompt == "这张图是什么"
        return VisionResult(
            scene_summary="疑似灵山大佛景区照片",
            detected_text="灵山胜境",
            candidate_attractions=("灵山大佛",),
            visual_tags=("佛像", "景区"),
            query_hints=("拍照识景",),
            confidence=0.88,
            provider="fake",
        )

    async def aclose(self) -> None:
        return None


def _post_vision(content=None, content_type="image/jpeg", params=None):
    """helper to reduce boilerplate in MIME/size tests"""
    headers = {}
    if content is None:
        name = {"image/jpeg": "tiny.jpg", "image/png": "tiny.png", "image/webp": "tiny.webp"}.get((content_type or "").split(";")[0], "tiny.jpg")
        content = (_IMAGES / name).read_bytes()
    if content_type is not None:
        headers["Content-Type"] = content_type
    return TestClient(app).post(
        "/api/vision/analyze",
        params=params or {},
        content=content,
        headers=headers,
    )


def test_vision_analyze_api_returns_retrieval_query() -> None:
    app.dependency_overrides[get_vision_service] = lambda: FakeVisionService()
    try:
        response = TestClient(app).post(
            "/api/vision/analyze",
            params={"question": "这张图是什么", "filename": "lingshan.jpg"},
            content=(_IMAGES / "tiny.jpg").read_bytes(),
            headers={"Content-Type": "image/jpeg"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "fake"
    assert data["scene_summary"] == "疑似灵山大佛景区照片"
    assert data["detected_text"] == "灵山胜境"
    assert data["candidate_attractions"] == ["灵山大佛"]
    assert data["visual_tags"] == ["佛像", "景区"]
    assert data["confidence"] == 0.88
    assert data["retrieval_query"].startswith("这张图是什么；")
    assert "灵山大佛" in data["retrieval_query"]


def test_vision_idempotency_reuses_result_and_rejects_key_mismatch() -> None:
    class CountingVision(BaseVisionService):
        calls = 0
        async def analyze(self, content, *, filename=None, mime_type=None, prompt=None):
            self.calls += 1
            return VisionResult(scene_summary="景区照片", provider="fake")
        async def aclose(self):
            return None

    service = CountingVision()
    app.dependency_overrides[get_vision_service] = lambda: service
    try:
        client = TestClient(app)
        image = (_IMAGES / "tiny.jpg").read_bytes()
        headers = {"Content-Type": "image/jpeg", "Idempotency-Key": "vision-test-key"}
        first = client.post("/api/vision/analyze", content=image, headers=headers)
        retry = client.post("/api/vision/analyze", content=image, headers=headers)
        conflict = client.post("/api/vision/analyze", content=image, params={"question": "different"}, headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert conflict.status_code == 409
    assert service.calls == 1


def test_vision_analyze_api_rejects_empty_body() -> None:
    response = _post_vision(content=b"", content_type="image/jpeg")
    assert response.status_code == 400


# ── MIME whitelist tests ──

def test_vision_allows_jpeg() -> None:
    response = _post_vision(content_type="image/jpeg")
    assert response.status_code == 200


def test_vision_allows_png() -> None:
    response = _post_vision(content_type="image/png")
    assert response.status_code == 200


def test_vision_allows_webp() -> None:
    response = _post_vision(content_type="image/webp")
    assert response.status_code == 200


def test_vision_allows_mime_with_charset_param() -> None:
    response = _post_vision(content_type="image/jpeg; charset=binary")
    assert response.status_code == 200


def test_vision_rejects_gif() -> None:
    response = _post_vision(content_type="image/gif")
    assert response.status_code == 415
    assert "仅支持" in response.json()["detail"]


def test_vision_rejects_text_plain() -> None:
    response = _post_vision(content_type="text/plain")
    assert response.status_code == 415
    assert "仅支持" in response.json()["detail"]


def test_vision_rejects_missing_content_type() -> None:
    response = _post_vision(content_type=None)
    assert response.status_code == 415
    assert "仅支持" in response.json()["detail"]


def test_vision_rejects_octet_stream() -> None:
    response = _post_vision(content_type="application/octet-stream")
    assert response.status_code == 415
    assert "仅支持" in response.json()["detail"]


# ── size limit test ──

def test_vision_rejects_over_5mb() -> None:
    big = b"x" * (5 * 1024 * 1024 + 1)
    response = _post_vision(content=big, content_type="image/jpeg")
    assert response.status_code == 413


def test_vision_rejects_mime_that_does_not_match_actual_image() -> None:
    response = _post_vision(content=(_IMAGES / "tiny.png").read_bytes(), content_type="image/jpeg")
    assert response.status_code == 415


def test_vision_rejects_a_truncated_image() -> None:
    response = _post_vision(content=(_IMAGES / "tiny.png").read_bytes()[:25], content_type="image/png")
    assert response.status_code == 400


def test_vision_rejects_image_exceeding_pixel_limit() -> None:
    app.dependency_overrides[get_app_settings] = lambda: Settings(vision_max_image_pixels=5)
    try:
        response = _post_vision(content=(_IMAGES / "tiny.png").read_bytes(), content_type="image/png")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 413


def test_webp_rejects_canvas_that_lies_about_encoded_dimensions() -> None:
    original = (_IMAGES / "tiny.webp").read_bytes()
    # Extended 1x1 canvas wrapping a real 2x3 VP8 frame.
    vp8x = b"VP8X" + (10).to_bytes(4, "little") + b"\0" * 10
    chunks = vp8x + original[12:]
    forged = b"RIFF" + (len(chunks) + 4).to_bytes(4, "little") + b"WEBP" + chunks
    assert _post_vision(content=forged, content_type="image/webp").status_code == 400


def test_webp_rejects_a_second_encoded_image_frame() -> None:
    original = (_IMAGES / "tiny.webp").read_bytes()
    chunk = original[12:]
    # Reuse the real image chunk with a corrected RIFF length.
    chunks = chunk + chunk
    forged = b"RIFF" + (len(chunks) + 4).to_bytes(4, "little") + b"WEBP" + chunks
    assert _post_vision(content=forged, content_type="image/webp").status_code == 400


def test_jpeg_rejects_conflicting_frame_dimensions() -> None:
    original = (_IMAGES / "tiny.jpg").read_bytes()
    # The fixture has one baseline SOF segment at byte 158. Add a second
    # frame declaration with a different width before the first scan.
    second_sof = bytearray(original[158:177])
    second_sof[7] ^= 1
    forged = original[:177] + bytes(second_sof) + original[177:]
    assert _post_vision(content=forged, content_type="image/jpeg").status_code == 400


def test_jpeg_with_trailing_camera_metadata_is_accepted() -> None:
    content = (_IMAGES / "tiny.jpg").read_bytes() + b"camera extra metadata"
    assert _post_vision(content=content, content_type="image/jpeg").status_code == 200


def test_animated_webp_has_a_clear_unsupported_format_error() -> None:
    original = (_IMAGES / "tiny.webp").read_bytes()
    vp8x = b"VP8X" + (10).to_bytes(4, "little") + b"\x02" + b"\0" * 9
    chunks = vp8x + original[12:]
    content = b"RIFF" + (len(chunks) + 4).to_bytes(4, "little") + b"WEBP" + chunks
    response = _post_vision(content=content, content_type="image/webp")
    assert response.status_code == 415
    assert "动态" in response.json()["detail"]


def test_vision_over_capacity_returns_clear_busy_status() -> None:
    limiter = CapacityLimiter({"vision": 1})
    lease = limiter.try_acquire("vision")
    app.state.guide_capacity = limiter
    try:
        response = _post_vision(content=(_IMAGES / "tiny.png").read_bytes(), content_type="image/png")
        assert response.status_code == 429
    finally:
        lease.release()
        del app.state.guide_capacity
