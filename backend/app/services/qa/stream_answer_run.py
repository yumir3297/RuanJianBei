from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import aclosing

from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_generation_run import StreamGenerationOutcome


class StreamAnswerRun:
    """Own the generation-to-completion SSE stream for one answer."""

    def __init__(
        self,
        *,
        generation_run,
        completion_factory: Callable[[StreamGenerationOutcome], AsyncIterator[StreamEvent]],
    ) -> None:
        self.generation_run = generation_run
        self.completion_factory = completion_factory

    async def events(self) -> AsyncIterator[StreamEvent]:
        generation_events = self.generation_run.events()
        async with aclosing(generation_events) as source:
            async for event in source:
                yield event

        outcome = self.generation_run.outcome
        if outcome is None:
            raise RuntimeError("stream generation ended without an outcome")
        if outcome.error_event is not None:
            yield outcome.error_event
            return
        if outcome.finalized is None:
            raise RuntimeError("stream generation completed without finalization")

        completion_events = self.completion_factory(outcome)
        async with aclosing(completion_events) as source:
            async for event in source:
                yield event
