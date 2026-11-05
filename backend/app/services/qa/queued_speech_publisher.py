from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_events import StreamEvent
from app.services.tts.base import TTSAudio

logger = logging.getLogger(__name__)


class QueuedSpeechPublisher:
    """Render one sentence and publish its ordered avatar/audio SSE events."""

    def __init__(
        self,
        *,
        tts_service,
        avatar_service,
        audio_event_builder: Callable[[str, str, int, str], StreamEvent],
        emotion_resolver: Callable[[], str],
    ) -> None:
        self.tts_service = tts_service
        self.avatar_service = avatar_service
        self.audio_event_builder = audio_event_builder
        self.emotion_resolver = emotion_resolver

    async def __call__(
        self,
        sentence: str,
        queue: QueuedStreamEvents,
        *,
        previous: asyncio.Task[None] | None = None,
        semaphore: asyncio.Semaphore | None = None,
        notify=None,
    ) -> None:
        async def synthesize() -> TTSAudio:
            try:
                return await self.tts_service.synthesize(sentence)
            except Exception:
                logger.exception("TTS sentence synthesis failed; preserving text")
                return TTSAudio(base64_audio="", duration_ms=0, provider="tts_unavailable")

        if semaphore is None:
            audio = await synthesize()
        else:
            async with semaphore:
                audio = await synthesize()
        avatar = await self.avatar_service.drive(sentence)
        if previous is not None:
            await previous
        await queue.publish(
            (
                StreamEvent(
                    type="avatar",
                    data={"viseme_text": avatar.viseme_text, "emotion": self.emotion_resolver()},
                ),
                self.audio_event_builder(
                    sentence,
                    audio.base64_audio,
                    audio.duration_ms,
                    audio.provider,
                ),
            ),
            notify=notify,
        )
