from __future__ import annotations

import asyncio
import base64
import logging
import time

import httpx

from app.core.config import Settings
from app.services.asr.base import ASRResult, BaseASRService


logger = logging.getLogger(__name__)


class QwenASRService(BaseASRService):
    """DashScope multimodal-generation ASR via OpenAI-compatible API Key.

    Uses fun-asr-flash model which supports synchronous transcription with
    base64-encoded audio (no public URL required). Supports Chinese dialects.

    Endpoint: POST dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
    """

    requires_public_audio_url = False

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self._owns_client = client is None

    async def transcribe(self, content: bytes | str) -> ASRResult:
        started_at = time.perf_counter()
        if not self._is_configured():
            return self._unavailable("Qwen ASR 配置不完整。", started_at=started_at)
        if isinstance(content, str):
            return self._unavailable("Qwen ASR 需要原始音频字节。", started_at=started_at)
        if not content:
            return self._unavailable("音频内容为空。", started_at=started_at)

        try:
            client = self._client or self._build_client()
            async with asyncio.timeout(self.settings.asr_timeout_seconds):
                text = await self._transcribe_bytes(client, content)
        except Exception as exc:
            logger.warning("Qwen ASR failed with %s.", type(exc).__name__)
            return self._unavailable(
                self._safe_error_message(exc),
                started_at=started_at,
                error_type=type(exc).__name__,
            )

        return ASRResult(
            text=text,
            confidence=0.85 if text else 0.0,
            duration_ms=self._elapsed_ms(started_at),
            provider="qwen",
            confidence_source="heuristic",
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _transcribe_bytes(self, client: httpx.AsyncClient, content: bytes) -> str:
        audio_b64 = base64.b64encode(content).decode()
        fmt = self._detect_format(content)
        parameters: dict[str, str] = {"format": fmt, "sample_rate": "16000"}
        if self.settings.asr_vocabulary_id.strip():
            parameters["vocabulary_id"] = self.settings.asr_vocabulary_id.strip()
        payload = {
            "model": self.settings.asr_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": f"data:audio/{fmt};base64,{audio_b64}"
                                },
                            }
                        ],
                    }
                ]
            },
            "parameters": parameters,
        }

        response = await client.post(
            self.settings.asr_base_url,
            headers={
                "Authorization": f"Bearer {self.settings.asr_api_key}",
                "Content-Type": "application/json",
                "X-DashScope-SSE": "disable",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        logger.debug("Qwen ASR response: %s", data)

        output = data.get("output", {})
        inner = output.get("output", {})
        sentence = inner.get("sentence", {})
        if isinstance(sentence, dict) and sentence.get("text"):
            return sentence["text"].strip()

        top_text = output.get("text")
        if isinstance(top_text, str) and top_text.strip():
            return top_text.strip()

        return ""

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=min(5.0, self.settings.asr_timeout_seconds),
            read=self.settings.asr_timeout_seconds,
            write=self.settings.asr_timeout_seconds,
            pool=min(5.0, self.settings.asr_timeout_seconds),
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    def _is_configured(self) -> bool:
        return bool(
            self.settings.asr_api_key.strip()
            and self.settings.asr_base_url.strip()
            and self.settings.asr_model.strip()
        )

    def _unavailable(
        self,
        message: str,
        *,
        started_at: float,
        error_type: str | None = None,
    ) -> ASRResult:
        error_message = message
        if error_type:
            error_message = f"{message} ({error_type})"
        return ASRResult(
            text="",
            confidence=0.0,
            duration_ms=self._elapsed_ms(started_at),
            provider="qwen_unavailable",
            confidence_source="unavailable",
            error_message=error_message,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"Qwen ASR 返回 HTTP {exc.response.status_code}。"
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "Qwen ASR 请求超时。"
        if isinstance(exc, httpx.RequestError):
            return "Qwen ASR 网络请求失败。"
        return str(exc)[:200] or "Qwen ASR 暂时不可用。"

    @staticmethod
    def _detect_format(content: bytes) -> str:
        """Detect audio format from magic bytes. Defaults to wav (what the frontend sends)."""
        if content[:4] == b"RIFF":
            return "wav"
        if content[:4] == b"\x1a\x45\xdf\xa3":
            return "webm"
        if content[:3] == b"ID3" or (content[0] == 0xff and (content[1] & 0xe0) == 0xe0):
            return "mp3"
        return "wav"
