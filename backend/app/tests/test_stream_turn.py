import asyncio

import pytest

from app.services.llm.types import LLMStreamEvent
from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_turn import StreamTurn


def create_turn(llm_source, audio_worker, *, text_only=True, epoch_is_current=None):
    if epoch_is_current is None:
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
async def test_stream_turn_delivers_unsent_http_audio_tail_in_fifo_order():
    spoken = []

    async def source():
        yield LLMStreamEvent(type="finish", finish_reason="stop")

    async def audio_worker(sentence, queue, *, previous, semaphore, notify):
        del semaphore
        if previous is not None:
            await previous
        spoken.append(sentence)
        await queue.publish([
            StreamEvent("avatar", {"text": sentence}),
            StreamEvent("audio", {"text": sentence}),
        ], notify=notify)

    turn = create_turn(source(), audio_worker, text_only=False)
    _ = [event async for event in turn.events()]
    turn.answer_buffer.append("未发送尾句。")

    events = [event async for event in turn.final_audio_events(
        faq_documents_present=False, text_only=False, streaming_requested=False,
    )]

    assert spoken == ["未发送尾句。"]
    assert [event.type for event in events] == ["avatar", "audio"]
    assert [event.data["text"] for event in events] == ["未发送尾句。", "未发送尾句。"]
    assert turn.audio_visibility_changed is False


@pytest.mark.asyncio
async def test_stream_turn_withholds_stale_http_audio_after_epoch_change():
    async def source():
        yield LLMStreamEvent(type="finish", finish_reason="stop")

    async def audio_worker(sentence, queue, *, previous, semaphore, notify):
        del previous, semaphore, notify
        await queue.publish([StreamEvent("audio", {"text": sentence})])

    async def stale_epoch():
        return False

    turn = create_turn(source(), audio_worker, text_only=False, epoch_is_current=stale_epoch)
    _ = [event async for event in turn.events()]
    turn.answer_buffer.append("旧知识尾句。")

    events = [event async for event in turn.final_audio_events(
        faq_documents_present=False, text_only=False, streaming_requested=False,
    )]

    assert [event.type for event in events] == ["error"]
    assert events[0].data["message"] == "知识内容已更新，已停止继续输出。"
    assert turn.audio_visibility_changed is True


@pytest.mark.asyncio
async def test_closing_final_audio_delivery_cancels_later_scheduled_audio():
    second_audio_started = asyncio.Event()
    second_audio_cancelled = asyncio.Event()

    async def source():
        yield LLMStreamEvent(type="finish", finish_reason="stop")

    async def audio_worker(sentence, queue, *, previous, semaphore, notify):
        del semaphore
        if previous is not None:
            await previous
        if sentence == "first":
            await queue.publish([StreamEvent("audio", {"text": sentence})], notify=notify)
            return
        second_audio_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            second_audio_cancelled.set()

    turn = create_turn(source(), audio_worker, text_only=True)
    _ = [event async for event in turn.events()]
    turn.schedule_audio("first")
    turn.schedule_audio("second")
    events = turn.final_audio_events(
        faq_documents_present=False, text_only=True, streaming_requested=False,
    )

    assert (await anext(events)).type == "audio"
    await asyncio.wait_for(second_audio_started.wait(), timeout=1)
    await events.aclose()

    assert second_audio_cancelled.is_set(), "aclose must finish cancelling queued speech before returning"
    await asyncio.wait_for(second_audio_cancelled.wait(), timeout=1)
    assert turn.audio_group.pending == ()


@pytest.mark.asyncio
async def test_stream_turn_completion_check_cancels_audio_and_reraises_llm_error():
    audio_started = asyncio.Event()
    audio_cancelled = asyncio.Event()

    async def source():
        yield LLMStreamEvent(type="content", text="第一句。")
        raise RuntimeError("LLM stream failed")

    async def audio_worker(sentence, queue, **kwargs):
        del sentence, queue, kwargs
        audio_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            audio_cancelled.set()

    turn = create_turn(source(), audio_worker, text_only=False)
    events = [event async for event in turn.events()]
    await asyncio.wait_for(audio_started.wait(), timeout=1)

    with pytest.raises(RuntimeError, match="LLM stream failed"):
        await turn.check_generation_result()

    await asyncio.wait_for(audio_cancelled.wait(), timeout=1)
    assert any(event.type == "text_chunk" for event in events)
    assert turn.audio_group.pending == ()


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
