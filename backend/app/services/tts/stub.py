from __future__ import annotations

import base64

from app.services.tts.base import BaseTTSService, TTSAudio


class StubTTSService(BaseTTSService):
    async def synthesize(self, text: str) -> TTSAudio:
        payload = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        duration_ms = max(800, len(text) * 90)
        return TTSAudio(base64_audio=payload, duration_ms=duration_ms, provider="stub")
