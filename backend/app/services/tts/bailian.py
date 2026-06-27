import base64
import logging
from typing import Any

import httpx

from app.services.tts.base import BaseTTSService, TTSAudio


logger = logging.getLogger(__name__)

NATIVE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
COMPATIBLE_TTS_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/speech"


class BailianTTSService(BaseTTSService):
    def __init__(
        self,
        api_key: str,
        base_url: str = NATIVE_TTS_URL,
        model: str = "cosyvoice-v3-flash",
        voice: str = "longwan_v3",
        timeout_seconds: float = 30.0,
        use_compatible_api: bool = False,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.voice = voice
        self.timeout_seconds = timeout_seconds
        self.use_compatible_api = use_compatible_api

    async def synthesize(self, text: str) -> TTSAudio:
        if not text.strip():
            return TTSAudio(base64_audio="", duration_ms=0, provider="bailian")

        if self.use_compatible_api:
            return await self._synthesize_compatible(text)
        return await self._synthesize_native(text)

    async def _synthesize_compatible(self, text: str) -> TTSAudio:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "mp3",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                audio_data = base64.b64encode(response.content).decode("ascii")
                duration_ms = self._estimate_duration(text)
                logger.info(
                    "Bailian TTS (compatible) success: model=%s voice=%s chars=%d",
                    self.model,
                    self.voice,
                    len(text),
                )
                return TTSAudio(
                    base64_audio=audio_data,
                    duration_ms=duration_ms,
                    provider="bailian",
                )
        except httpx.HTTPStatusError as exc:
            error_code = ""
            error_message = ""
            request_id = ""
            try:
                err_body = exc.response.json()
                error_code = err_body.get("code", "")
                error_message = err_body.get("message", "")
                request_id = err_body.get("request_id", "")
            except ValueError:
                error_message = exc.response.text[:200]
            logger.error(
                "Bailian TTS (compatible) failed: status=%s code=%s message=%s request_id=%s",
                exc.response.status_code,
                error_code,
                error_message,
                request_id,
            )
            return TTSAudio(
                base64_audio="",
                duration_ms=0,
                provider="bailian_unavailable",
            )
        except Exception:
            logger.exception("Bailian TTS (compatible) synthesis failed.")
            return TTSAudio(
                base64_audio="",
                duration_ms=0,
                provider="bailian_unavailable",
            )

    async def _synthesize_native(self, text: str) -> TTSAudio:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": {
                "text": text,
            },
            "parameters": {
                "voice": self.voice,
                "format": "mp3",
                "sample_rate": 24000,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                if response.headers.get("content-type", "").lower().startswith("audio/"):
                    audio_data = base64.b64encode(response.content).decode("ascii")
                    return TTSAudio(
                        base64_audio=audio_data,
                        duration_ms=self._estimate_duration(text),
                        provider="bailian",
                    )

                result = response.json()
                audio_data = await self._resolve_audio_data(result, client)
                if not audio_data:
                    logger.warning(
                        "Bailian TTS returned no audio: code=%s message=%s request_id=%s",
                        result.get("code", ""),
                        result.get("message", ""),
                        result.get("request_id", ""),
                    )
                    return TTSAudio(
                        base64_audio="",
                        duration_ms=0,
                        provider="bailian_unavailable",
                    )

                duration_ms = self._extract_duration_ms(result) or self._estimate_duration(text)
                return TTSAudio(
                    base64_audio=audio_data,
                    duration_ms=duration_ms,
                    provider="bailian",
                )

        except httpx.HTTPStatusError as exc:
            error_code = ""
            error_message = ""
            request_id = ""
            try:
                err_body = exc.response.json()
                error_code = err_body.get("code", "")
                error_message = err_body.get("message", "")
                request_id = err_body.get("request_id", "")
            except ValueError:
                error_message = exc.response.text[:200]
            logger.error(
                "Bailian TTS (native) failed: status=%s code=%s message=%s request_id=%s",
                exc.response.status_code,
                error_code,
                error_message,
                request_id,
            )
            return TTSAudio(
                base64_audio="",
                duration_ms=0,
                provider="bailian_unavailable",
            )
        except Exception:
            logger.exception("Bailian TTS (native) synthesis failed.")
            return TTSAudio(
                base64_audio="",
                duration_ms=0,
                provider="bailian_unavailable",
            )

    async def _resolve_audio_data(
        self,
        result: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> str:
        output = result.get("output") or {}
        audio_value = output.get("audio") or output.get("audio_url")

        if isinstance(audio_value, dict):
            audio_value = (
                audio_value.get("data")
                or audio_value.get("base64")
                or audio_value.get("url")
            )

        if not isinstance(audio_value, str) or not audio_value.strip():
            return ""

        audio_value = audio_value.strip()
        if audio_value.startswith(("http://", "https://")):
            audio_response = await client.get(audio_value)
            audio_response.raise_for_status()
            return base64.b64encode(audio_response.content).decode("ascii")

        if audio_value.startswith("data:") and "," in audio_value:
            return audio_value.split(",", 1)[1]

        return audio_value

    @staticmethod
    def _extract_duration_ms(result: dict[str, Any]) -> int:
        output = result.get("output") or {}
        for key in ("duration_ms", "audio_duration_ms"):
            value = output.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)

        duration = output.get("duration")
        if isinstance(duration, (int, float)) and duration > 0:
            return int(duration * 1000)
        return 0

    def _estimate_duration(self, text: str) -> int:
        char_count = len(text)
        return int(char_count * 200)
