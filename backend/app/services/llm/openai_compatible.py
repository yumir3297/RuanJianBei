from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import Settings
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_builder import EvidencePromptBuilder
from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.rag.base import RetrievedDocument


logger = logging.getLogger(__name__)


class OpenAICompatibleLLMService(BaseLLMService):
    _semaphores: dict[tuple[int, int], asyncio.Semaphore] = {}

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
        prompt_builder: EvidencePromptBuilder | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self._owns_client = client is None
        self.prompt_builder = prompt_builder or EvidencePromptBuilder(
            max_documents=settings.llm_max_evidence_documents,
            max_chars_per_document=settings.llm_max_evidence_chars_per_document,
        )

    async def stream_generate(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        persona: str | None = None,
    ):
        if not documents:
            yield LLMStreamEvent(
                type="content",
                text="根据现有景区资料，暂时无法确定。",
            )
            yield LLMStreamEvent(type="finish", finish_reason="no_evidence")
            return

        if self.settings.llm_provider == "stub":
            async for event in self._stream_fallback(documents, reason="stub"):
                yield event
            return

        if not self._is_configured():
            logger.error("LLM provider configuration is incomplete; using evidence fallback.")
            async for event in self._stream_fallback(documents, reason="configuration_error"):
                yield event
            return

        emitted_content = False
        try:
            async for event in self._stream_provider(query, documents, persona=persona):
                if event.type == "content" and event.text:
                    emitted_content = True
                yield event
        except Exception as exc:
            logger.warning("LLM provider failed with %s; using evidence fallback.", type(exc).__name__)
            if emitted_content:
                yield LLMStreamEvent(
                    type="content",
                    text="\n\n（AI讲解连接中断，请以右侧官方来源为准。）",
                )
                yield LLMStreamEvent(
                    type="finish",
                    finish_reason=f"interrupted_{self._error_reason(exc)}",
                )
                return
            async for event in self._stream_fallback(documents, reason=self._error_reason(exc)):
                yield event

    async def _stream_provider(
        self,
        query: str,
        documents: list[RetrievedDocument],
        *,
        persona: str | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        prompt = self.prompt_builder.build(query, documents, persona=persona)
        client = self._client or self._build_client()
        semaphore = self._get_semaphore(self.settings.llm_max_concurrency)
        payload = {
            "model": self.settings.llm_model,
            "messages": prompt.messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }

        async with semaphore:
            async with asyncio.timeout(self.settings.llm_total_timeout_seconds):
                async with client.stream(
                    "POST",
                    self._chat_completions_url(self.settings.llm_base_url),
                    headers={
                        "Authorization": f"Bearer {self.settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    iterator = self._iter_sse_payloads(response.aiter_lines()).__aiter__()
                    loop = asyncio.get_running_loop()
                    first_token_deadline = loop.time() + self.settings.llm_first_token_timeout_seconds
                    received_content = False

                    while True:
                        timeout = self.settings.llm_read_timeout_seconds
                        if not received_content:
                            timeout = max(0.01, first_token_deadline - loop.time())
                        try:
                            raw_payload = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
                        except StopAsyncIteration:
                            break
                        if raw_payload == "[DONE]":
                            break
                        chunk = self._parse_payload(raw_payload)
                        if chunk is None:
                            continue

                        usage = self._parse_usage(chunk.get("usage"))
                        if usage is not None:
                            yield LLMStreamEvent(type="usage", usage=usage)

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        delta = choice.get("delta") or {}
                        text = str(delta.get("content") or "")
                        if text:
                            received_content = True
                            yield LLMStreamEvent(type="content", text=text)
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            yield LLMStreamEvent(
                                type="finish",
                                finish_reason=str(finish_reason),
                            )

                    if not received_content:
                        raise RuntimeError("LLM stream completed without answer content.")

    async def _stream_fallback(
        self,
        documents: list[RetrievedDocument],
        *,
        reason: str,
    ) -> AsyncIterator[LLMStreamEvent]:
        parts = ["AI讲解服务暂时不可用，先为你展示检索到的官方资料："]
        for index, document in enumerate(
            documents[: self.settings.llm_max_evidence_documents],
            start=1,
        ):
            content = (document.snippet or document.content).strip()
            if content:
                parts.append(f"[证据{index}] {content[:180]}")
        text = "\n".join(parts)
        yield LLMStreamEvent(type="content", text=text)
        yield LLMStreamEvent(type="finish", finish_reason=f"fallback_{reason}")

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=self.settings.llm_connect_timeout_seconds,
            read=self.settings.llm_read_timeout_seconds,
            write=self.settings.llm_read_timeout_seconds,
            pool=self.settings.llm_connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _is_configured(self) -> bool:
        return all(
            (
                self.settings.llm_api_key.strip(),
                self.settings.llm_base_url.strip(),
                self.settings.llm_model.strip(),
            )
        )

    @classmethod
    def _get_semaphore(cls, limit: int) -> asyncio.Semaphore:
        loop_id = id(asyncio.get_running_loop())
        key = (loop_id, limit)
        semaphore = cls._semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(limit)
            cls._semaphores[key] = semaphore
        return semaphore

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    @staticmethod
    async def _iter_sse_payloads(lines: AsyncIterator[str]) -> AsyncIterator[str]:
        async for line in lines:
            if line.startswith("data:"):
                yield line[5:].strip()

    @staticmethod
    def _parse_payload(payload: str) -> dict[str, Any] | None:
        if not payload.strip():
            return None
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _parse_usage(payload: Any) -> LLMUsage | None:
        if not isinstance(payload, dict):
            return None
        details = payload.get("prompt_tokens_details") or {}
        return LLMUsage(
            prompt_tokens=int(payload.get("prompt_tokens") or 0),
            completion_tokens=int(payload.get("completion_tokens") or 0),
            total_tokens=int(payload.get("total_tokens") or 0),
            cached_tokens=int(details.get("cached_tokens") or 0),
        )

    @staticmethod
    def _error_reason(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"http_{exc.response.status_code}"
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "timeout"
        if isinstance(exc, httpx.RequestError):
            return "network"
        return "provider_error"
