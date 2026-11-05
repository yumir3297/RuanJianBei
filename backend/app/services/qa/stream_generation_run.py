from __future__ import annotations

from contextlib import aclosing
from dataclasses import dataclass
from typing import Any

from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_generation_finalizer import (
    FinalizedStreamGeneration,
    finalize_stream_generation,
)


@dataclass(frozen=True)
class StreamGenerationOutcome:
    stream_turn: Any
    streaming_requested: bool
    error_event: StreamEvent | None
    finalized: FinalizedStreamGeneration | None


class StreamGenerationRun:
    """Own one generated answer's event drain, error check, and terminal decision."""

    def __init__(self, *, turn_factory, turn_kwargs: dict, finalization_kwargs: dict) -> None:
        self.turn_factory = turn_factory
        self.turn_kwargs = turn_kwargs
        self.finalization_kwargs = finalization_kwargs
        self.outcome: StreamGenerationOutcome | None = None

    async def events(self):
        stream_turn, streaming_requested = self.turn_factory.create(**self.turn_kwargs)
        async with aclosing(stream_turn.events()) as source:
            async for event in source:
                yield event

        error_event = await stream_turn.check_generation_result()
        finalized = None
        if error_event is None:
            finalized = finalize_stream_generation(
                generated_answer=stream_turn.answer_buffer.full_answer,
                finish_reason=stream_turn.llm_finish_reason,
                **self.finalization_kwargs,
            )
            stream_turn.answer_buffer.full_answer = finalized.answer

        self.outcome = StreamGenerationOutcome(
            stream_turn=stream_turn,
            streaming_requested=streaming_requested,
            error_event=error_event,
            finalized=finalized,
        )
