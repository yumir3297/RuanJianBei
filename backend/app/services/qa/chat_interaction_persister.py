from __future__ import annotations

import logging

from app.repositories.chat_log import ChatLogRepository
from app.schemas.chat import ChatRequest
from app.services.emotion import EmotionResponsePolicy, EmotionSignal, FusedEmotion
from app.services.qa.request_profile import (
    extract_interests,
    infer_audience_type,
    resolve_narration_audience,
)

logger = logging.getLogger(__name__)


class ChatInteractionPersister:
    """Persist one completed answer and best-effort visitor aggregates."""

    def __init__(
        self,
        *,
        chat_log_repository,
        visitor_repository,
        visitor_memory_repository,
        speech_profile: dict | None,
    ) -> None:
        self.chat_log_repository = chat_log_repository
        self.visitor_repository = visitor_repository
        self.visitor_memory_repository = visitor_memory_repository
        self.speech_profile = speech_profile

    async def persist(
        self,
        *,
        session_id: str,
        raw_query: str,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        latency_ms: int,
        request: ChatRequest,
        active_subject: str | None,
        text_emotion: EmotionSignal | None,
        audio_emotion: EmotionSignal | None,
        fused_emotion: FusedEmotion,
        response_policy: EmotionResponsePolicy,
    ) -> int:
        create_kwargs = dict(
            session_id=session_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            answer=answer,
            sources=sources,
            hit_level=hit_level,
            latency_ms=latency_ms,
        )
        if self.speech_profile is not None and not request.text_only:
            from app.services.tts.speech_profile import answer_fingerprint, build_speech_cache_key

            metadata = dict(self.speech_profile)
            metadata["answer_version"] = answer_fingerprint(answer)
            metadata["cache_key"] = build_speech_cache_key(answer, self.speech_profile)
            create_kwargs["speech_metadata"] = metadata
        if isinstance(self.chat_log_repository, ChatLogRepository):
            create_kwargs.update(
                input_mode=request.input_mode,
                text_emotion=text_emotion.label.value if text_emotion is not None else "neutral",
                audio_emotion=(
                    audio_emotion.label.value
                    if audio_emotion is not None and audio_emotion.available
                    else None
                ),
                fused_emotion=fused_emotion.label.value,
                emotion_confidence=fused_emotion.confidence,
                emotion_intensity=fused_emotion.intensity,
                emotion_conflict=fused_emotion.conflict,
                emotion_modalities=list(fused_emotion.modalities),
                response_strategy=response_policy.label.value,
            )
        log = await self.chat_log_repository.create(**create_kwargs)
        if self.visitor_repository is not None:
            try:
                await self.visitor_repository.upsert(
                    session_id=session_id,
                    interests=extract_interests(request),
                    audience_type=infer_audience_type(request),
                )
            except Exception:
                logger.exception("Visitor profile update failed.")
        if self.visitor_memory_repository is not None and request.visitor_id:
            try:
                await self.visitor_memory_repository.record_visit(
                    visitor_id=request.visitor_id,
                    session_id=session_id,
                    attraction_title=active_subject,
                    interests=extract_interests(request),
                    narration_audience=resolve_narration_audience(request),
                )
            except Exception:
                logger.exception("Visitor memory write failed.")
        return log.id
