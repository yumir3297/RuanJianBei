from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_answer_run import StreamAnswerRun


def test_generation_error_is_forwarded_and_completion_is_skipped() -> None:
    error = StreamEvent("error", {"message": "stale"})

    class Generation:
        outcome = None

        async def events(self):
            yield StreamEvent("text_chunk", {"text": "partial"})
            self.outcome = SimpleNamespace(error_event=error, finalized=None)

    completion_called = False

    def completion_factory(_outcome):
        nonlocal completion_called
        completion_called = True
        raise AssertionError("generation error must skip completion")

    run = StreamAnswerRun(
        generation_run=Generation(),
        completion_factory=completion_factory,
    )

    events = asyncio.run(collect(run.events()))

    assert [event.type for event in events] == ["text_chunk", "error"]
    assert events[-1] is error
    assert completion_called is False


def test_closing_generation_stream_skips_completion_and_closes_source() -> None:
    class Generation:
        outcome = None
        closed = False

        async def events(self):
            try:
                yield StreamEvent("text_chunk", {"text": "partial"})
            finally:
                self.closed = True

    generation = Generation()
    completion_called = False

    def completion_factory(_outcome):
        nonlocal completion_called
        completion_called = True
        raise AssertionError("closed generation must not enter completion")

    run = StreamAnswerRun(
        generation_run=generation,
        completion_factory=completion_factory,
    )

    async def scenario():
        events = run.events()
        assert (await anext(events)).type == "text_chunk"
        await events.aclose()

    asyncio.run(scenario())

    assert generation.closed is True
    assert completion_called is False


def test_closing_completion_stream_closes_nested_generator() -> None:
    class Generation:
        outcome = SimpleNamespace(
            error_event=None,
            finalized=object(),
        )

        async def events(self):
            yield StreamEvent("text_chunk", {"text": "answer"})

    class Completion:
        closed = False

        async def events(self):
            try:
                yield StreamEvent("text", {"text": "final answer"})
                await asyncio.Event().wait()
            finally:
                self.closed = True

    completion = Completion()
    run = StreamAnswerRun(
        generation_run=Generation(),
        completion_factory=lambda _outcome: completion.events(),
    )

    async def scenario():
        events = run.events()
        assert (await anext(events)).type == "text_chunk"
        assert (await anext(events)).type == "text"
        await events.aclose()

    asyncio.run(scenario())

    assert completion.closed is True


def test_task_cancellation_during_generation_closes_source_and_skips_completion() -> None:
    class Generation:
        outcome = None

        def __init__(self):
            self.started = asyncio.Event()
            self.closed = False

        async def events(self):
            try:
                self.started.set()
                await asyncio.Event().wait()
                yield StreamEvent("text_chunk", {"text": "never emitted"})
            finally:
                self.closed = True

    generation = Generation()
    completion_called = False

    def completion_factory(_outcome):
        nonlocal completion_called
        completion_called = True
        raise AssertionError("cancelled generation must not start completion")

    run = StreamAnswerRun(
        generation_run=generation,
        completion_factory=completion_factory,
    )

    async def scenario():
        consumer = asyncio.create_task(collect(run.events()))
        await generation.started.wait()
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert generation.closed is True
    assert completion_called is False


def test_task_cancellation_during_completion_closes_completion_iterator() -> None:
    class Generation:
        outcome = SimpleNamespace(error_event=None, finalized=object())

        async def events(self):
            yield StreamEvent("text_chunk", {"text": "answer"})

    class Completion:
        def __init__(self):
            self.started = asyncio.Event()
            self.closed = False

        async def events(self):
            try:
                self.started.set()
                await asyncio.Event().wait()
                yield StreamEvent("text", {"text": "never emitted"})
            finally:
                self.closed = True

    completion = Completion()
    run = StreamAnswerRun(
        generation_run=Generation(),
        completion_factory=lambda _outcome: completion.events(),
    )

    async def scenario():
        consumer = asyncio.create_task(collect(run.events()))
        await completion.started.wait()
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert completion.closed is True


async def collect(events):
    return [event async for event in events]
