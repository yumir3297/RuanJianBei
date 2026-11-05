from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.services.qa.stream_events import StreamEvent


class FinalAnswerSpeechEmitter:
    """Render the optional speech/avatar tail for a completed fast-path answer."""

    def __init__(
        self,
        *,
        tts_service,
        avatar_service,
        audio_event_builder: Callable[[str, str, int, str], StreamEvent],
        emotion_resolver: Callable[[str, int], str],
        epoch_is_current: Callable[[int | None], Awaitable[bool]],
    ) -> None:
        self.tts_service = tts_service
        self.avatar_service = avatar_service
        self.audio_event_builder = audio_event_builder
        self.emotion_resolver = emotion_resolver
        self.epoch_is_current = epoch_is_current

    async def render(
        self,
        *,
        answer: str,
        hit_level: str,
        sources: list[dict],
        expected_epoch: int | None,
    ) -> list[StreamEvent]:
        tts_text = self._speech_text(answer, hit_level)
        render_tasks = [
            asyncio.create_task(self.tts_service.synthesize(tts_text)),
            asyncio.create_task(self.avatar_service.drive(tts_text)),
        ]
        try:
            audio, avatar = await asyncio.gather(*render_tasks)
        except BaseException:
            for task in render_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*render_tasks, return_exceptions=True)
            raise
        if not await self.epoch_is_current(expected_epoch):
            return [StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})]

        avatar_data = {
            "viseme_text": avatar.viseme_text,
            "emotion": self.emotion_resolver(hit_level, len(sources)),
        }
        if avatar.action:
            avatar_data["action"] = avatar.action
        return [
            StreamEvent(type="avatar", data=avatar_data),
            self.audio_event_builder(
                tts_text,
                audio.base64_audio,
                audio.duration_ms,
                audio.provider,
            ),
        ]

    @staticmethod
    def _speech_text(answer: str, hit_level: str) -> str:
        # Keep long FAQ narration responsive without changing the visible answer.
        if not hit_level.startswith("faq_") or len(answer) <= 150:
            return answer
        tts_text = answer[:150]
        last_period = tts_text.rfind("。")
        if last_period > 80:
            return tts_text[: last_period + 1]
        return tts_text.rstrip() + "……"
