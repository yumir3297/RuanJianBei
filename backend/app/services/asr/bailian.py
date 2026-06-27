from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import Settings
from app.services.asr.base import ASRResult, BaseASRService


logger = logging.getLogger(__name__)


class BailianASRService(BaseASRService):
    """DashScope Paraformer recorded-speech ASR service.

    The recorded-speech API pulls audio from a public file URL. Raw browser blobs
    must be exposed by the API layer before this service can submit a task.
    """

    requires_public_audio_url = True

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
            return self._unavailable("百炼 ASR 配置不完整。", started_at=started_at)
        if isinstance(content, bytes):
            return self._unavailable("百炼录音文件识别需要可公网访问的音频 URL。", started_at=started_at)

        audio_url = content.strip()
        if not audio_url:
            return self._unavailable("音频 URL 为空。", started_at=started_at)

        try:
            client = self._client or self._build_client()
            async with asyncio.timeout(self.settings.asr_timeout_seconds):
                task_id = await self._submit_task(client, audio_url)
                task_payload = await self._poll_task(client, task_id)
                text = await self._extract_text(client, task_payload)
        except Exception as exc:
            logger.warning("Bailian ASR failed with %s.", type(exc).__name__)
            return self._unavailable(
                self._safe_error_message(exc),
                started_at=started_at,
                error_type=type(exc).__name__,
            )

        return ASRResult(
            text=text,
            confidence=0.78 if text else 0.0,
            duration_ms=self._elapsed_ms(started_at),
            provider="bailian",
            confidence_source="heuristic",
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=min(5.0, self.settings.asr_timeout_seconds),
            read=self.settings.asr_timeout_seconds,
            write=self.settings.asr_timeout_seconds,
            pool=min(5.0, self.settings.asr_timeout_seconds),
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def _submit_task(self, client: httpx.AsyncClient, audio_url: str) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.asr_model,
            "input": {
                "file_urls": [audio_url],
            },
            "parameters": {},
        }
        if self.settings.asr_vocabulary_id.strip():
            payload["parameters"]["vocabulary_id"] = self.settings.asr_vocabulary_id.strip()

        response = await client.post(
            self.settings.asr_base_url,
            headers={
                "Authorization": f"Bearer {self.settings.asr_api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        task_id = self._dig(data, "output", "task_id") or data.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Bailian ASR response did not include task_id.")
        return task_id.strip()

    async def _poll_task(self, client: httpx.AsyncClient, task_id: str) -> dict[str, Any]:
        task_url = f"{self.settings.asr_task_url.rstrip('/')}/{task_id}"
        while True:
            response = await client.get(
                task_url,
                headers={"Authorization": f"Bearer {self.settings.asr_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            status = str(self._dig(data, "output", "task_status") or data.get("task_status") or "").upper()
            if status in {"SUCCEEDED", "SUCCESS"}:
                return data
            if status in {"FAILED", "CANCELED", "CANCELLED"}:
                message = self._dig(data, "output", "message") or data.get("message") or "Bailian ASR task failed."
                raise RuntimeError(str(message))
            await asyncio.sleep(self.settings.asr_poll_interval_seconds)

    async def _extract_text(self, client: httpx.AsyncClient, task_payload: dict[str, Any]) -> str:
        direct_text = self._find_text(task_payload)
        if direct_text:
            return direct_text

        results = self._dig(task_payload, "output", "results") or task_payload.get("results") or []
        if isinstance(results, dict):
            results = [results]
        transcription_urls = [
            item.get("transcription_url")
            for item in results
            if isinstance(item, dict) and isinstance(item.get("transcription_url"), str)
        ]
        texts: list[str] = []
        for url in transcription_urls:
            response = await client.get(url)
            response.raise_for_status()
            texts.append(self._find_text(response.json()))
        return " ".join(item for item in texts if item).strip()

    @classmethod
    def _find_text(cls, payload: Any) -> str:
        if isinstance(payload, str):
            return payload.strip()
        if not isinstance(payload, dict):
            return ""

        for key in ("text", "transcript", "sentence"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        output_text = cls._dig(payload, "output", "text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        parts: list[str] = []
        for key in ("transcripts", "sentences", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    text = cls._find_text(item)
                    if text:
                        parts.append(text)
        return " ".join(parts).strip()

    def _is_configured(self) -> bool:
        return all(
            (
                self.settings.asr_api_key.strip(),
                self.settings.asr_base_url.strip(),
                self.settings.asr_task_url.strip(),
                self.settings.asr_model.strip(),
            )
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
            provider="bailian_unavailable",
            confidence_source="unavailable",
            error_message=error_message,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.perf_counter() - started_at) * 1000)

    @staticmethod
    def _dig(payload: dict[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"百炼 ASR 返回 HTTP {exc.response.status_code}。"
        if isinstance(exc, (httpx.TimeoutException, TimeoutError, TimeoutError)):
            return "百炼 ASR 请求超时。"
        if isinstance(exc, httpx.RequestError):
            return "百炼 ASR 网络请求失败。"
        return str(exc)[:200] or "百炼 ASR 暂时不可用。"
