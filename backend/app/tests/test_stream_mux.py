from types import SimpleNamespace

import asyncio
from types import SimpleNamespace

import pytest

from app.services.llm.types import LLMStreamEvent, LLMUsage
from app.services.qa.queued_stream_events import QueuedStreamEvents
from app.services.qa.stream_answer import StreamAnswerBuffer
from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_mux import StreamMuxState, get_epoch_guarded_message
from app.services.qa.stream_mux_consumer import StreamMuxConsumer
from app.services.qa.streaming_tts_buffer import StreamingTTSBuffer


def test_stream_mux_tracks_terminal_events_and_tts_fallback_progress():
    mux = StreamMuxState(streaming_requested=True)

    assert mux.consume("llm", "token").llm_payload == "token"
    mux.consume("tts_connected", None)
    delivery = mux.consume(
        "tts",
        SimpleNamespace(type="word_timestamps", data={"characters": 7}),
    )
    assert delivery.tts_payload.type == "word_timestamps"
    assert mux.tts_confirmed_chars == 7

    mux.consume("tts", SimpleNamespace(type="error", data={}))
    assert mux.tts_failed
    assert mux.tts_done

    mux.consume("llm_done", None)
    assert mux.llm_done


def test_stream_mux_marks_connection_failure_for_http_fallback():
    mux = StreamMuxState(streaming_requested=True)

    delivery = mux.consume("tts_connect_error", RuntimeError("offline"))

    assert delivery.warning == "connect"
    assert mux.tts_failed
    assert mux.tts_done


def test_streaming_tts_buffer_flushes_at_existing_phrase_boundaries():
    buffer = StreamingTTSBuffer()

    buffer.append("短句。")
    assert buffer.take_ready() == "短句。"
    assert buffer.take_ready() is None

    buffer.append("逗号分段，")
    assert buffer.take_ready() is None
    buffer.append("再加三字，")
    assert buffer.take_ready() == "逗号分段，再加三字，"


def test_streaming_tts_buffer_drains_unfinished_tail_once():
    buffer = StreamingTTSBuffer()
    buffer.append("尾部未完成")

    assert buffer.drain() == "尾部未完成"
    assert buffer.drain() is None


@pytest.mark.asyncio
async def test_epoch_guarded_mux_read_drops_message_if_epoch_changes_during_wait():
    queue = asyncio.Queue()
    await queue.put(("llm", "stale token"))
    checks = iter([True, False])

    async def epoch_is_current():
        return next(checks)

    assert await get_epoch_guarded_message(queue, epoch_is_current) is None
    assert queue.empty()


@pytest.mark.asyncio
async def test_epoch_guarded_mux_read_does_not_wait_when_epoch_is_already_stale():
    queue = asyncio.Queue()

    async def epoch_is_current():
        return False

    assert await get_epoch_guarded_message(queue, epoch_is_current) is None
    assert queue.empty()


@pytest.mark.asyncio
async def test_stream_mux_consumer_emits_text_and_keeps_usage_and_finish_metadata():
    queue = asyncio.Queue()
    usage = LLMUsage(prompt_tokens=2, completion_tokens=3, total_tokens=5)
    events = [
        LLMStreamEvent(type="usage", usage=usage),
        LLMStreamEvent(type="content", text="回答完成。"),
        LLMStreamEvent(type="finish", finish_reason="stop"),
        None,
    ]
    for kind, payload in zip(("llm", "llm", "llm", "llm_done"), events):
        await queue.put((kind, payload))

    class Controller:
        async def flush_ready(self):
            return None

        async def finish_if_ready(self):
            return None

    async def epoch_is_current():
        return True

    consumer = StreamMuxConsumer(
        queue=queue,
        mux_state=StreamMuxState(streaming_requested=False),
        epoch_is_current=epoch_is_current,
        answer_buffer=StreamAnswerBuffer(),
        audio_events=QueuedStreamEvents(),
        schedule_audio=lambda sentence: pytest.fail(f"unexpected speech task: {sentence}"),
        streaming_tts_buffer=SimpleNamespace(append=lambda token: None),
        streaming_tts_controller=Controller(),
        streaming_requested=False,
        text_only=True,
        faq_documents_present=False,
        adapt_tts_event=lambda event: (StreamEvent(type="audio", data={"event": event}),),
        coerce_llm_event=lambda event: event,
    )

    emitted = [event async for event in consumer.events()]

    assert [(event.type, event.data) for event in emitted] == [
        ("text_chunk", {"token": "回答完成。"})
    ]
    assert consumer.answer_buffer.full_answer == "回答完成。"
    assert consumer.llm_usage == usage
    assert consumer.llm_finish_reason == "stop"
    assert not consumer.visibility_changed
