from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.services.vision.base import BaseVisionService, VisionResult


logger = logging.getLogger(__name__)


class QwenVisionService(BaseVisionService):
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self._owns_client = client is None

    async def analyze(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionResult:
        if not self._is_configured():
            return self._fallback_result("Qwen 图片识别配置不完整。", filename=filename, mime_type=mime_type)

        try:
            payload = self._build_payload(content, mime_type=mime_type, prompt=prompt)
            client = self._client or self._build_client()
            async with asyncio.timeout(self.settings.vision_total_timeout_seconds):
                response = await client.post(
                    self._chat_completions_url(self.settings.vision_base_url),
                    headers={
                        "Authorization": f"Bearer {self.settings.vision_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            response.raise_for_status()
            return self._parse_response(response.json(), filename=filename, mime_type=mime_type)
        except Exception as exc:
            logger.warning("Qwen vision provider failed with %s.", type(exc).__name__)
            return self._fallback_result(
                "图片识别服务暂时不可用，当前图片只能作为低置信度检索线索。",
                filename=filename,
                mime_type=mime_type,
                error_type=type(exc).__name__,
                error_message=self._safe_error_message(exc),
            )

    def _build_payload(
        self,
        content: bytes,
        *,
        mime_type: str | None,
        prompt: str | None,
    ) -> dict[str, Any]:
        image_mime = mime_type or "image/jpeg"
        image_url = f"data:{image_mime};base64,{base64.b64encode(content).decode('ascii')}"
        user_prompt = prompt or "请识别这张景区图片，提取可用于景区资料检索的线索。"
        return {
            "model": self.settings.vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是景区图片识别助手。只输出 JSON，不要输出 Markdown。"
                        "图片识别结果只能作为检索线索，不能当作景区事实来源。"
                        "JSON 字段必须包含 scene_summary, detected_text, "
                        "candidate_attractions, visual_tags, query_hints, confidence。"
                        "candidate_attractions、visual_tags、query_hints 必须是字符串数组；"
                        "confidence 是 0 到 1 的数字。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            "stream": False,
            "temperature": 0.1,
        }

    def _parse_response(
        self,
        payload: dict[str, Any],
        *,
        filename: str | None,
        mime_type: str | None,
    ) -> VisionResult:
        content = self._extract_message_content(payload)
        parsed = self._parse_jsonish_content(content)
        return VisionResult(
            scene_summary=self._as_text(parsed.get("scene_summary")),
            detected_text=self._as_text(parsed.get("detected_text")),
            candidate_attractions=self._as_text_tuple(parsed.get("candidate_attractions")),
            visual_tags=self._as_text_tuple(parsed.get("visual_tags")),
            query_hints=self._as_text_tuple(parsed.get("query_hints")),
            confidence=self._as_confidence(parsed.get("confidence")),
            provider="qwen",
            raw={
                "filename": filename,
                "mime_type": mime_type,
                "model": self.settings.vision_model,
            },
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=self.settings.vision_connect_timeout_seconds,
            read=self.settings.vision_read_timeout_seconds,
            write=self.settings.vision_read_timeout_seconds,
            pool=self.settings.vision_connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    def _is_configured(self) -> bool:
        return all(
            (
                self.settings.vision_api_key.strip(),
                self.settings.vision_base_url.strip(),
                self.settings.vision_model.strip(),
            )
        )

    def _fallback_result(
        self,
        scene_summary: str,
        *,
        filename: str | None,
        mime_type: str | None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> VisionResult:
        raw: dict[str, Any] = {
            "filename": filename,
            "mime_type": mime_type,
            "model": self.settings.vision_model,
        }
        if error_type:
            raw["error_type"] = error_type
        if error_message:
            raw["error_message"] = error_message
        return VisionResult(
            scene_summary=scene_summary,
            query_hints=tuple(value for value in (filename,) if value),
            confidence=0.0,
            provider="qwen",
            raw=raw,
        )

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return ""

    @staticmethod
    def _parse_jsonish_content(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"scene_summary": text}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                    return parsed if isinstance(parsed, dict) else {"scene_summary": text}
                except json.JSONDecodeError:
                    pass
        return {"scene_summary": text}

    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list | tuple):
            return "；".join(item for item in (QwenVisionService._as_text(item) for item in value) if item)
        if isinstance(value, dict):
            for key in ("text", "content", "value"):
                if key in value:
                    return QwenVisionService._as_text(value[key])
            return ""
        text = str(value).strip()
        return "" if text in {"[]", "{}", "null", "None"} else text

    @classmethod
    def _as_text_tuple(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list | tuple):
            return tuple(item for item in (cls._as_text(item) for item in value) if item)
        text = cls._as_text(value)
        return (text,) if text else ()

    @staticmethod
    def _as_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"Qwen vision returned HTTP {exc.response.status_code}."
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "Qwen vision request timed out."
        if isinstance(exc, httpx.RequestError):
            return "Qwen vision network request failed."
        return str(exc)[:200]
