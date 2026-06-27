from __future__ import annotations

from pathlib import Path

from app.services.vision.base import BaseVisionService, VisionResult


class StubVisionService(BaseVisionService):
    async def analyze(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        mime_type: str | None = None,
        prompt: str | None = None,
    ) -> VisionResult:
        filename_hint = Path(filename).stem if filename else ""
        query_hints = tuple(
            value
            for value in (
                prompt,
                filename_hint,
            )
            if value
        )
        return VisionResult(
            scene_summary="图片识别真实模型尚未接入，当前结果仅用于本地流程占位。",
            query_hints=query_hints,
            confidence=0.0,
            provider="stub",
            raw={
                "byte_size": len(content),
                "filename": filename,
                "mime_type": mime_type,
            },
        )
