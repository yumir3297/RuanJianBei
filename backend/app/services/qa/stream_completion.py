from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_events import StreamEvent


def final_audio_segments(
    answer: StreamAnswerBuffer,
    *,
    faq_documents_present: bool,
    text_only: bool,
    streaming_requested: bool,
    streaming_tts_failed: bool,
    tts_confirmed_chars: int,
) -> tuple[str, ...]:
    """Choose only the unsent answer text that needs HTTP TTS at stream completion."""
    if text_only:
        return ()

    if faq_documents_present:
        text = answer.full_answer.strip()
    elif streaming_requested and streaming_tts_failed:
        text = answer.full_answer[tts_confirmed_chars:].strip()
    elif not streaming_requested:
        text = answer.sentence_buffer.strip()
    else:
        text = ""

    return (text,) if text else ()


class AudioTaskDrainer:
    """Wait for HTTP TTS tasks and publish their SSE events only at a current epoch."""

    def __init__(
        self,
        *,
        tasks: Iterable[asyncio.Task[None]],
        audio_events: QueuedStreamEvents,
        epoch_is_current: Callable[[], Awaitable[bool]],
        cancel_audio: Callable[[], Awaitable[None]],
    ) -> None:
        self.tasks = tuple(tasks)
        self.audio_events = audio_events
        self.epoch_is_current = epoch_is_current
        self.cancel_audio = cancel_audio
        self.visibility_changed = False

    async def events(self) -> AsyncIterator[StreamEvent]:
        for task in self.tasks:
            await task
            if not await self.epoch_is_current():
                self.visibility_changed = True
                await self.cancel_audio()
                return
            for event in self.audio_events.drain():
                yield event


class StreamCompletionCoordinator:
    """Keep post-generation audio, cancellation, epoch fences, and terminal SSE ordered."""

    async def events(
        self,
        *,
        stream_turn,
        answer: str,
        faq_text_sent: bool,
        incomplete: bool,
        faq_documents_present: bool,
        text_only: bool,
        streaming_requested: bool,
        epoch_is_current: Callable[[], Awaitable[bool]],
        cache_answer: Callable[[], Awaitable[None]] | None,
        persist_answer: Callable[[], Awaitable[str | None]],
        followups_event: Callable[[], StreamEvent],
        done_event: Callable[[str | None], StreamEvent],
        after_audio: Callable[[], Awaitable[None]] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        try:
            if faq_text_sent:
                yield StreamEvent(type="text", data={"text": answer, "is_complete": True})

            audio_events = stream_turn.final_audio_events(
                faq_documents_present=faq_documents_present,
                text_only=text_only,
                streaming_requested=streaming_requested,
            )
            try:
                async for event in audio_events:
                    yield event
            finally:
                await audio_events.aclose()
            if stream_turn.audio_visibility_changed:
                return

            if after_audio is not None:
                await after_audio()
            if not await epoch_is_current():
                yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
                return
            if cache_answer is not None:
                await cache_answer()
            chat_log_id = await persist_answer()
            if not await epoch_is_current():
                yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
                return
            if not faq_text_sent:
                yield StreamEvent(type="text", data={"text": answer, "is_complete": not incomplete})
            yield followups_event()
            yield done_event(chat_log_id)
        except BaseException:
            await stream_turn.cancel_audio()
            raise
