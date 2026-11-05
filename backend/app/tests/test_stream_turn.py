import asyncio

import pytest

from app.services.llm.types import LLMStreamEvent
from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_turn import StreamTurn


def create_turn(llm_source, audio_worker, *, text_only=True):
    async def epoch_is_current():
        return True

    return StreamTurn(
        llm_source=llm_source,
        tts_session=None,
        streaming_requested=False,
        text_only=text_only,
        faq_documents_present=False,
        epoch_is_current=epoch_is_current,
        audio_worker=audio_worker,
        adapt_tts_event=lambda event: (StreamEvent("audio", {"event": event}),),
        coerce_llm_event=lambda event: event if isinstance(event, LLMStreamEvent) else LLMStreamEvent(
            type="content", text=str(event)
        ),
    )


@pytest.mark.asyncio
async def test_stream_turn_emits_tokens_and_exposes_terminal_metadata():
    source_closed = asyncio.Event()

    async def source():
        try:
            yield LLMStreamEvent(type="content", text="山门在东侧。")
            yield LLMStreamEvent(type="usage")
            yield LLMStreamEvent(type="finish", finish_reason="stop")
        finally:
            source_closed.set()

    async def audio_worker(sentence, queue, **kwargs):
        del sentence, queue, kwargs
        raise AssertionError("text-only turns must not schedule audio")

    turn = create_turn(source(), audio_worker)
    events = [event async for event in turn.events()]

    assert [(event.type, event.data["token"]) for event in events] == [
        ("text_chunk", "山门在东侧。")
    ]
    assert turn.answer_buffer.full_answer == "山门在东侧。"
    assert turn.llm_finish_reason == "stop"
    assert turn.llm_usage.completion_tokens == 0
    assert source_closed.is_set()


@pytest.mark.asyncio
async def test_closing_stream_turn_cancels_speech_and_closes_llm_source():
    audio_started = asyncio.Event()
    audio_closed = asyncio.Event()
    source_closed = asyncio.Event()

    async def source():
        try:
            yield LLMStreamEvent(type="content", text="请看这边。")
            await asyncio.Event().wait()
        finally:
            source_closed.set()

    async def audio_worker(sentence, queue, **kwargs):
        del sentence, queue, kwargs
        audio_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            audio_closed.set()

    turn = create_turn(source(), audio_worker, text_only=False)
    turn.schedule_audio("请看这边。")
    events = turn.events()
    first_event = await anext(events)
    await asyncio.wait_for(audio_started.wait(), timeout=1)
    await events.aclose()

    assert first_event.type == "text_chunk"
    assert source_closed.is_set()
    assert audio_closed.is_set()
    assert turn.audio_group.pending == ()
