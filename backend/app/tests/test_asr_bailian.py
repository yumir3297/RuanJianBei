from __future__ import annotations

import asyncio
import json

import httpx

from app.core.config import Settings
from app.services.asr.bailian import BailianASRService


def asr_settings(**overrides) -> Settings:
    values = {
        "asr_provider": "bailian",
        "asr_api_key": "test-asr-key",
        "asr_model": "paraformer-v2",
        "asr_base_url": "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription",
        "asr_task_url": "https://dashscope.aliyuncs.com/api/v1/tasks",
        "asr_vocabulary_id": "vocab-lingshan",
        "asr_timeout_seconds": 3,
        "asr_poll_interval_seconds": 0.01,
    }
    values.update(overrides)
    return Settings(**values)


def test_bailian_asr_submits_task_and_reads_transcription_url() -> None:
    async def run():
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                assert request.url == "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
                assert request.headers["authorization"] == "Bearer test-asr-key"
                assert request.headers["x-dashscope-async"] == "enable"
                payload = json.loads(request.content)
                assert payload["model"] == "paraformer-v2"
                assert payload["input"]["file_urls"] == ["https://public.example.com/audio.webm"]
                assert payload["parameters"]["vocabulary_id"] == "vocab-lingshan"
                return httpx.Response(200, json={"output": {"task_id": "task-1"}})

            if str(request.url).endswith("/api/v1/tasks/task-1"):
                return httpx.Response(
                    200,
                    json={
                        "output": {
                            "task_status": "SUCCEEDED",
                            "results": [
                                {
                                    "transcription_url": "https://result.example.com/task-1.json",
                                }
                            ],
                        }
                    },
                )

            if str(request.url) == "https://result.example.com/task-1.json":
                return httpx.Response(
                    200,
                    json={"transcripts": [{"text": "灵山大佛有八十八米高"}]},
                )

            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = BailianASRService(asr_settings(), client=client)
            return await service.transcribe("https://public.example.com/audio.webm")

    result = asyncio.run(run())

    assert result.provider == "bailian"
    assert result.text == "灵山大佛有八十八米高"
    assert result.confidence == 0.78
    assert result.confidence_source == "heuristic"
    assert result.needs_confirmation is True


def test_bailian_asr_reports_unavailable_for_raw_bytes() -> None:
    service = BailianASRService(asr_settings())

    async def run():
        return await service.transcribe(b"local-webm-bytes")

    result = asyncio.run(run())

    assert result.provider == "bailian_unavailable"
    assert result.confidence_source == "unavailable"
    assert result.needs_confirmation is True
    assert "公网访问" in result.error_message
