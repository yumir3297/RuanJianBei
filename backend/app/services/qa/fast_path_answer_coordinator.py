from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from time import perf_counter

from app.services.qa.stream_events import StreamEvent


class FastPathAnswerCoordinator:
    """Preserve SSE, speech, epoch, persistence, and terminal ordering for fast answers."""

    def __init__(self, *, speech_emitter, epoch_is_current: Callable[[int | None], Awaitable[bool]]) -> None:
        self.speech_emitter = speech_emitter
        self.epoch_is_current = epoch_is_current

    async def events(
        self,
        *,
        answer: str,
        sources: list[dict],
        hit_level: str,
        text_only: bool,
        expected_epoch: int | None,
        start: float,
        prepare_answer: Callable[[str, list[dict]], str],
        persist_answer: Callable[[str, int], Awaitable[int | None]],
        followups_event: Callable[[], StreamEvent],
        done_event: Callable[[int | None, int], StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        if not await self.epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return

        answer = prepare_answer(answer, sources)
        if sources:
            yield StreamEvent(type="sources", data={"docs": sources})
        if not await self.epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return

        yield StreamEvent(type="text", data={"text": answer, "is_complete": True})
        if not text_only:
            speech_events = await self.speech_emitter.render(
                answer=answer,
                hit_level=hit_level,
                sources=sources,
                expected_epoch=expected_epoch,
            )
            for event in speech_events:
                yield event
            if any(event.type == "error" for event in speech_events):
                return

        if not await self.epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return

        latency_ms = int((perf_counter() - start) * 1000)
        chat_log_id = await persist_answer(answer, latency_ms)
        if not await self.epoch_is_current(expected_epoch):
            yield StreamEvent(type="error", data={"message": "知识内容已更新，请重新提问。"})
            return
        yield followups_event()
        yield done_event(chat_log_id, latency_ms)
