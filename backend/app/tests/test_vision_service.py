from __future__ import annotations

import asyncio

from app.services.vision import StubVisionService, VisionResult


def test_vision_result_builds_deduplicated_retrieval_query() -> None:
    result = VisionResult(
        scene_summary="疑似灵山大佛广场",
        detected_text="灵山胜境",
        candidate_attractions=("灵山大佛", "灵山大佛"),
        visual_tags=("佛像", "广场"),
        query_hints=("灵山大佛", "拍照识景"),
        provider="test",
    )

    query = result.as_retrieval_query("这是什么景点")

    assert query.startswith("这是什么景点；")
    assert "疑似灵山大佛广场" in query
    assert "灵山胜境" in query
    assert query.split("；").count("灵山大佛") == 1
    assert "拍照识景" in query


def test_stub_vision_service_returns_non_authoritative_hint() -> None:
    service = StubVisionService()

    result = asyncio.run(
        service.analyze(
            b"fake-image-bytes",
            filename="lingshan-buddha.jpg",
            mime_type="image/jpeg",
            prompt="帮我识别这张图",
        )
    )

    assert result.provider == "stub"
    assert result.confidence == 0.0
    assert "真实模型尚未接入" in result.scene_summary
    assert result.raw["byte_size"] == len(b"fake-image-bytes")
    assert "帮我识别这张图" in result.as_retrieval_query()
    assert "lingshan-buddha" in result.as_retrieval_query()
