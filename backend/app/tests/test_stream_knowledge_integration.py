"""Cross-check K01 epoch visibility once its branch is present."""
import asyncio
import inspect

import pytest

from app.schemas.chat import ChatRequest
from app.services.tts.base import TTSAudio
from app.services.qa.pipeline import QAPipeline
from app.tests.test_pipeline import _build_test_pipeline


def _require_visibility_support():
    if "visibility_service" not in inspect.signature(QAPipeline).parameters:
        pytest.skip("K01 visibility implementation is not present on this checkout")


def test_epoch_change_cancels_pending_http_speech():
    _require_visibility_support()

    async def scenario():
        started = asyncio.Event()
        canceled = asyncio.Event()
        state = {"epoch": 1}

        class Visibility:
            async def read_epoch(self):
                return state["epoch"]

        class LLM:
            async def stream_generate(self, *args, **kwargs):
                yield "第一句。"
                await started.wait()
                state["epoch"] = 2
                yield "不能继续。"

        class TTS:
            async def synthesize(self, text):
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    canceled.set()
                    raise

        pipeline = _build_test_pipeline(visibility_service=Visibility(), llm_service=LLM(), tts_service=TTS())
        events = [event async for event in pipeline.stream_chat(ChatRequest(query="讲解景点", session_id="epoch-change", text_only=False))]
        assert canceled.is_set()
        assert events[-1].type == "error"
        assert not any(event.type == "audio" for event in events)

    asyncio.run(scenario())


def test_epoch_change_during_final_audio_does_not_emit_stale_speech():
    _require_visibility_support()

    async def scenario():
        state = {"epoch": 1}

        class Visibility:
            async def read_epoch(self):
                return state["epoch"]

        class LLM:
            async def stream_generate(self, *args, **kwargs):
                yield "第一句。"

        class TTS:
            async def synthesize(self, text):
                state["epoch"] = 2
                await asyncio.sleep(0)
                return TTSAudio(base64_audio="AA==", duration_ms=100, provider="fake")

        pipeline = _build_test_pipeline(visibility_service=Visibility(), llm_service=LLM(), tts_service=TTS())
        events = [event async for event in pipeline.stream_chat(ChatRequest(query="讲解景点", session_id="epoch-audio", text_only=False))]
        assert events[-1].type == "error"
        assert not any(event.type == "audio" for event in events)

    asyncio.run(scenario())
