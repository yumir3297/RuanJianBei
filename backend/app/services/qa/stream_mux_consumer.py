from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_mux import StreamMuxState, get_epoch_guarded_message

logger = logging.getLogger(__name__)


class StreamMuxConsumer:
    """Consume one request's producer messages and preserve response event order."""

    def __init__(
        self,
        *,
        queue: asyncio.Queue[tuple[str, object | None]],
        mux_state: StreamMuxState,
        epoch_is_current: Callable[[], Awaitable[bool]],
        answer_buffer: StreamAnswerBuffer,
        audio_events: QueuedStreamEvents,
        schedule_audio: Callable[[str], object],
        streaming_tts_buffer,
        streaming_tts_controller,
        streaming_requested: bool,
        text_only: bool,
        faq_documents_present: bool,
        adapt_tts_event: Callable[[object], Iterable[StreamEvent]],
        coerce_llm_event: Callable[[LLMStreamEvent | str], LLMStreamEvent],
    ) -> None:
        self.queue = queue
        self.mux_state = mux_state
        self.epoch_is_current = epoch_is_current
        self.answer_buffer = answer_buffer
        self.audio_events = audio_events
        self.schedule_audio = schedule_audio
        self.streaming_tts_buffer = streaming_tts_buffer
        self.streaming_tts_controller = streaming_tts_controller
        self.streaming_requested = streaming_requested
        self.text_only = text_only
        self.faq_documents_present = faq_documents_present
        self.adapt_tts_event = adapt_tts_event
        self.coerce_llm_event = coerce_llm_event
        self.visibility_changed = False
        self.llm_usage = LLMUsage()
        self.llm_finish_reason: str | None = None

    async def events(self) -> AsyncIterator[StreamEvent]:
        while not self.mux_state.llm_done or not self.mux_state.tts_done:
            message = await get_epoch_guarded_message(self.queue, self.epoch_is_current)
            if message is None:
                self.visibility_changed = True
                break

            kind, payload = message
            delivery = self.mux_state.consume(kind, payload)
            if kind == "tts_connected":
                logger.info("Streaming TTS session started for chat")
            if delivery.warning == "connect":
                logger.warning(
                    "Streaming TTS unavailable; HTTP fallback will synthesize remaining text: %s",
                    type(payload).__name__,
                )
            elif delivery.warning == "mid_response":
                logger.warning("Streaming TTS failed mid-response; HTTP fallback will synthesize remaining text")
            if delivery.llm_error is not None:
                continue
            if delivery.tts_payload is not None:
                for sse in self.adapt_tts_event(delivery.tts_payload):
                    yield sse
            if delivery.drain_audio:
                for audio_event in self.audio_events.drain():
                    yield audio_event

            event = self.coerce_llm_event(delivery.llm_payload) if delivery.has_llm_payload else None
            if event is not None:
                if event.type == "usage":
                    self.llm_usage = event.usage
                    continue
                if event.type == "finish":
                    self.llm_finish_reason = event.finish_reason
                    continue
                token = event.text
                if not token:
                    continue
                self.answer_buffer.append(token)
                if not self.faq_documents_present:
                    yield StreamEvent(type="text_chunk", data={"token": token})

                if self.streaming_requested:
                    if not self.mux_state.tts_failed:
                        self.streaming_tts_buffer.append(token)
                elif not self.faq_documents_present:
                    for sentence in self.answer_buffer.take_speakable_sentences():
                        if not self.text_only:
                            self.schedule_audio(sentence)
                    for audio_event in self.audio_events.drain():
                        yield audio_event

            await self.streaming_tts_controller.flush_ready()
            await self.streaming_tts_controller.finish_if_ready()

            if (
                self.mux_state.llm_done
                and self.streaming_requested
                and not self.mux_state.tts_connected
                and self.mux_state.tts_failed
            ):
                self.mux_state.tts_done = True
