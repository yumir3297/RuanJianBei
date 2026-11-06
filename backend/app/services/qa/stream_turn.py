from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Iterable
from contextlib import aclosing

from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_completion import AudioTaskDrainer, final_audio_segments
from app.services.qa.audio_event_delivery import AudioEventDelivery
from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_lifecycle import AudioTaskGroup, StreamProducerGroup, stream_response_scope
from app.services.qa.stream_mux import StreamMuxState
from app.services.qa.stream_mux_consumer import StreamMuxConsumer
from app.services.qa.streaming_tts_buffer import StreamingTTSBuffer
from app.services.qa.streaming_tts_controller import StreamingTTSController


class StreamTurn:
    """Assemble and own the producer, mux consumer, and per-turn audio lifecycle."""

    def __init__(
        self,
        *,
        llm_source: AsyncIterable[LLMStreamEvent | str],
        tts_session,
        streaming_requested: bool,
        text_only: bool,
        faq_documents_present: bool,
        epoch_is_current: Callable[[], Awaitable[bool]],
        audio_worker: Callable[..., object],
        adapt_tts_event: Callable[[object], Iterable[StreamEvent]],
        coerce_llm_event: Callable[[LLMStreamEvent | str], LLMStreamEvent],
    ) -> None:
        self.audio_events = QueuedStreamEvents()
        self.audio_group = AudioTaskGroup(
            lambda sentence, **kwargs: audio_worker(sentence, self.audio_events, **kwargs)
        )
        self.answer_buffer = StreamAnswerBuffer()
        self.queue: asyncio.Queue[tuple[str, object | None]] = asyncio.Queue()
        self.finish_requested = asyncio.Event()
        self.mux_state = StreamMuxState(streaming_requested=streaming_requested)
        self.streaming_tts_buffer = StreamingTTSBuffer()
        self.streaming_tts_controller = StreamingTTSController(
            tts_session, self.mux_state, self.streaming_tts_buffer, self.finish_requested
        )

        self.producers = StreamProducerGroup(self.queue)
        self.producers.start_llm(llm_source)
        if tts_session is not None:
            self.producers.start_tts(tts_session, self.finish_requested)

        self.consumer = StreamMuxConsumer(
            queue=self.queue,
            mux_state=self.mux_state,
            epoch_is_current=epoch_is_current,
            answer_buffer=self.answer_buffer,
            audio_events=self.audio_events,
            schedule_audio=self.schedule_audio,
            streaming_tts_buffer=self.streaming_tts_buffer,
            streaming_tts_controller=self.streaming_tts_controller,
            streaming_requested=streaming_requested,
            text_only=text_only,
            faq_documents_present=faq_documents_present,
            adapt_tts_event=adapt_tts_event,
            coerce_llm_event=coerce_llm_event,
        )
        self._epoch_is_current = epoch_is_current
        self.audio_visibility_changed = False

    def schedule_audio(self, sentence: str) -> None:
        self.audio_group.schedule(sentence, notify=self.notify_audio)

    async def notify_audio(self) -> None:
        await self.queue.put(("audio_ready", None))

    async def cancel_audio(self) -> None:
        await self.audio_group.cancel()

    async def check_generation_result(self) -> StreamEvent | None:
        """Stop queued speech on failed or stale generation before returning control."""
        if self.llm_error is not None:
            await self.cancel_audio()
            raise self.llm_error
        if self.visibility_changed:
            await self.cancel_audio()
            return StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
        return None

    async def events(self) -> AsyncIterator[StreamEvent]:
        async with stream_response_scope(self.producers, self.cancel_audio):
            async for event in self.consumer.events():
                yield event

    async def final_audio_events(
        self,
        *,
        faq_documents_present: bool,
        text_only: bool,
        streaming_requested: bool,
    ) -> AsyncIterator[StreamEvent]:
        """Queue only unsent answer text, drain FIFO audio, and enforce the epoch fence."""
        for text in final_audio_segments(
            self.answer_buffer,
            faq_documents_present=faq_documents_present,
            text_only=text_only,
            streaming_requested=streaming_requested,
            streaming_tts_failed=self.mux_state.tts_failed,
            tts_confirmed_chars=self.mux_state.tts_confirmed_chars,
        ):
            self.schedule_audio(text)

        drainer = AudioTaskDrainer(
            tasks=self.audio_group.tasks,
            audio_events=self.audio_events,
            epoch_is_current=self._epoch_is_current,
            cancel_audio=self.cancel_audio,
        )
        delivery = AudioEventDelivery(drainer, self.cancel_audio)
        async with aclosing(delivery.events()) as events:
            async for event in events:
                yield event
        self.audio_visibility_changed = delivery.visibility_changed

    @property
    def llm_usage(self) -> LLMUsage:
        return self.consumer.llm_usage

    @property
    def llm_finish_reason(self) -> str | None:
        return self.consumer.llm_finish_reason

    @property
    def llm_error(self) -> Exception | None:
        return self.mux_state.llm_error

    @property
    def visibility_changed(self) -> bool:
        return self.consumer.visibility_changed
