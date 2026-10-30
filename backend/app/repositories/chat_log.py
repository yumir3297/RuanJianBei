from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog


class ChatLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        session_id: str,
        raw_query: str,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        latency_ms: int,
        input_mode: str = "text",
        text_emotion: str = "neutral",
        audio_emotion: str | None = None,
        fused_emotion: str = "neutral",
        emotion_confidence: float = 0.0,
        emotion_intensity: float = 0.0,
        emotion_conflict: bool = False,
        emotion_modalities: list[str] | None = None,
        response_strategy: str = "neutral",
        speech_metadata: dict | None = None,
    ) -> ChatLog:
        log = ChatLog(
            session_id=session_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            answer=answer,
            sources=json.dumps(sources, ensure_ascii=False),
            hit_level=hit_level,
            latency_ms=latency_ms,
            input_mode=input_mode,
            text_emotion=text_emotion,
            audio_emotion=audio_emotion,
            fused_emotion=fused_emotion,
            emotion_confidence=emotion_confidence,
            emotion_intensity=emotion_intensity,
            emotion_conflict=emotion_conflict,
            emotion_modalities=json.dumps(emotion_modalities or [], ensure_ascii=False),
            response_strategy=response_strategy,
            speech_metadata=(
                json.dumps(speech_metadata, ensure_ascii=False, sort_keys=True)
                if speech_metadata is not None
                else None
            ),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(ChatLog.id)))
        return result.scalar_one_or_none() or 0

    async def get_for_session(self, chat_log_id: int, session_id: str) -> ChatLog | None:
        result = await self.session.execute(
            select(ChatLog).where(
                ChatLog.id == chat_log_id,
                ChatLog.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def decode_speech_metadata(log: ChatLog) -> dict:
        if not log.speech_metadata:
            return {}
        try:
            value = json.loads(log.speech_metadata)
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
