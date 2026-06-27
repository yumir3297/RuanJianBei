from __future__ import annotations

from app.services.asr.base import ASRResult, BaseASRService


class StubASRService(BaseASRService):
    async def transcribe(self, content: bytes | str) -> ASRResult:
        if isinstance(content, bytes):
            text = "语音输入占位文本"
        else:
            text = content
        return ASRResult(
            text=text,
            confidence=0.0,
            provider="stub",
            confidence_source="stub",
            error_message="ASR provider is not configured.",
        )
