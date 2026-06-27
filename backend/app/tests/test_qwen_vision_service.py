from __future__ import annotations

import asyncio
import json

import httpx

from app.core.config import Settings
from app.services.vision.qwen import QwenVisionService


def qwen_settings(**overrides) -> Settings:
    values = {
        "vision_provider": "qwen",
        "vision_api_key": "test-qwen-key",
        "vision_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "vision_model": "qwen3.7-plus",
        "vision_connect_timeout_seconds": 1,
        "vision_read_timeout_seconds": 1,
        "vision_total_timeout_seconds": 3,
    }
    values.update(overrides)
    return Settings(**values)


def test_qwen_vision_service_sends_image_and_parses_json_result() -> None:
    async def run():
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            assert request.headers["authorization"] == "Bearer test-qwen-key"
            payload = json.loads(request.content)
            assert payload["model"] == "qwen3.7-plus"
            assert payload["stream"] is False
            user_content = payload["messages"][1]["content"]
            assert user_content[0]["type"] == "text"
            assert user_content[0]["text"] == "这是什么景点"
            assert user_content[1]["type"] == "image_url"
            assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "scene_summary": "画面中疑似灵山大佛广场。",
                                        "detected_text": "灵山胜境",
                                        "candidate_attractions": ["灵山大佛"],
                                        "visual_tags": ["佛像", "广场"],
                                        "query_hints": ["灵山大佛介绍"],
                                        "confidence": 0.82,
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QwenVisionService(qwen_settings(), client=client)
            return await service.analyze(
                b"fake-png-bytes",
                filename="buddha.png",
                mime_type="image/png",
                prompt="这是什么景点",
            )

    result = asyncio.run(run())

    assert result.provider == "qwen"
    assert result.scene_summary == "画面中疑似灵山大佛广场。"
    assert result.detected_text == "灵山胜境"
    assert result.candidate_attractions == ("灵山大佛",)
    assert result.visual_tags == ("佛像", "广场")
    assert result.query_hints == ("灵山大佛介绍",)
    assert result.confidence == 0.82
    assert "这是什么景点" in result.as_retrieval_query("这是什么景点")


def test_qwen_vision_service_ignores_empty_detected_text_array() -> None:
    async def run():
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "scene_summary": "图片中有大型佛像和山体背景。",
                                        "detected_text": [],
                                        "candidate_attractions": ["灵山大佛"],
                                        "visual_tags": ["佛像"],
                                        "query_hints": ["灵山大佛 正面"],
                                        "confidence": 0.9,
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QwenVisionService(qwen_settings(), client=client)
            return await service.analyze(b"fake-image", filename="buddha.jpg")

    result = asyncio.run(run())

    assert result.detected_text == ""
    assert "[]" not in result.as_retrieval_query("这张图是什么景点")
    assert "灵山大佛" in result.as_retrieval_query("这张图是什么景点")


def test_qwen_vision_service_falls_back_when_configuration_missing() -> None:
    service = QwenVisionService(qwen_settings(vision_api_key=""))

    async def run():
        return await service.analyze(b"fake-image", filename="unknown.jpg")

    result = asyncio.run(run())

    assert result.provider == "qwen"
    assert result.confidence == 0.0
    assert "配置不完整" in result.scene_summary
    assert "unknown.jpg" in result.as_retrieval_query()


def test_qwen_vision_service_fallback_records_provider_error() -> None:
    async def run():
        async def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow provider")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = QwenVisionService(qwen_settings(), client=client)
            return await service.analyze(b"fake-image", filename="slow.jpg")

    result = asyncio.run(run())

    assert result.provider == "qwen"
    assert result.confidence == 0.0
    assert "暂时不可用" in result.scene_summary
    assert result.raw["error_type"] == "ReadTimeout"
    assert result.raw["error_message"] == "Qwen vision request timed out."
