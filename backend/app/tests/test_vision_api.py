from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.api.vision import get_vision_service
from app.services.vision import BaseVisionService, VisionResult
from main import app


class FakeVisionService(BaseVisionService):
    async def analyze(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionResult:
        assert content == b"fake-jpeg-bytes"
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


def _post_vision(content=b"test-image", content_type="image/jpeg", params=None):
    """helper to reduce boilerplate in MIME/size tests"""
    headers = {}
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
            content=b"fake-jpeg-bytes",
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
