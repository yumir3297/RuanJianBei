from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.schemas.chat import ChatRequest
from app.services.qa.answer_styler import polish_answer
from app.services.qa.stream_answer_orchestrator import (
    StreamAnswerContext,
    StreamAnswerOrchestrator,
)
from app.services.qa.stream_events import StreamEvent
from app.services.rag.base import RetrievedDocument


class RecordingCompletion:
    def __init__(self) -> None:
        self.kwargs = None

    def events(self, **kwargs):
        self.kwargs = kwargs

        async def source():
            if kwargs["cache_answer"] is not None:
                await kwargs["cache_answer"]()
            yield StreamEvent("text", {"text": kwargs["answer"]})
            yield StreamEvent("done")

        return source()


class RecordingCache:
    def __init__(self) -> None:
        self.writes = []

    async def set(self, *args, **kwargs) -> None:
        self.writes.append((args, kwargs))


def _context() -> StreamAnswerContext:
    source = {"evidence_id": "faq-1"}
    return StreamAnswerContext(
        request=ChatRequest(
            query="原问题",
            session_id="orchestrator-test",
            persona="hanfu",
            text_only=True,
        ),
        documents=[RetrievedDocument(title="FAQ", content="权威资料", source="景区公告")],
        audience="adult",
        memory="偏好建筑",
        confirmed_visual_title="灵山大佛",
        vision_context_present=True,
        faq_documents_present=True,
        cache_allowed=True,
        llm_hit_level="faq_exact_styled",
        fallback_hit_level="faq_exact_styled_llm_fallback",
        faq_answer="权威 FAQ 答案",
        faq_sources=[source],
        normalized_query="规范问题",
        sources=[source],
        expected_epoch=7,
        start=1.0,
        cache_key="cache-key",
        resolved=SimpleNamespace(active_subject="灵山大佛"),
    )


def _orchestrator(turn_factory, completion, cache):
    async def epoch_is_current(_expected_epoch: int | None) -> bool:
        return True

    async def persist_interaction(**_kwargs) -> str:
        return "chat-log-1"

    return StreamAnswerOrchestrator(
        turn_factory=turn_factory,
        llm_provider_name="primary",
        emotion_aware_query=lambda query: f"warm:{query}",
        epoch_is_current=epoch_is_current,
        completion=completion,
        cache=cache,
        persist_interaction=persist_interaction,
        blind_spot_tracker=None,
        followup_event_builder=lambda resolved: StreamEvent(
            "followups", {"subject": resolved.active_subject}
        ),
        done_event_builder=lambda **kwargs: StreamEvent("done", kwargs),
    )


@pytest.mark.asyncio
async def test_orchestrator_keeps_faq_fallback_and_degraded_cache_guard() -> None:
    class Turn:
        def __init__(self) -> None:
            self.answer_buffer = SimpleNamespace(full_answer="")
            self.llm_finish_reason = "fallback_provider_error"
            self.llm_usage = SimpleNamespace(
                prompt_tokens=1, completion_tokens=2, total_tokens=3, cached_tokens=0
            )

        async def events(self):
            self.answer_buffer.full_answer = "未经证据支持的模型输出"
            yield StreamEvent("text_chunk", {"token": "部分输出"})

        async def check_generation_result(self):
            return None

    class TurnFactory:
        def __init__(self) -> None:
            self.kwargs = None
            self.turn = Turn()

        def create(self, **kwargs):
            self.kwargs = kwargs
            return self.turn, False

    turn_factory = TurnFactory()
    completion = RecordingCompletion()
    cache = RecordingCache()
    orchestrator = _orchestrator(turn_factory, completion, cache)

    events = [event async for event in orchestrator.events(_context())]

    assert [event.type for event in events] == ["text_chunk", "text", "done"]
    assert events[1].data["text"] == polish_answer(
        "权威 FAQ 答案", "hanfu", [{"evidence_id": "faq-1"}]
    )
    assert turn_factory.kwargs["memory"] == "偏好建筑"
    assert turn_factory.kwargs["confirmed_visual_title"] == "灵山大佛"
    assert completion.kwargs["cache_answer"] is None
    assert cache.writes == []


@pytest.mark.asyncio
async def test_closing_orchestrator_during_generation_closes_turn_and_skips_completion() -> None:
    class Turn:
        def __init__(self) -> None:
            self.answer_buffer = SimpleNamespace(full_answer="")
            self.llm_finish_reason = "stop"
            self.llm_usage = SimpleNamespace(
                prompt_tokens=0, completion_tokens=0, total_tokens=0, cached_tokens=0
            )
            self.started = asyncio.Event()
            self.closed = False

        async def events(self):
            try:
                self.started.set()
                yield StreamEvent("text_chunk", {"token": "部分答案"})
                await asyncio.Event().wait()
            finally:
                self.closed = True

        async def check_generation_result(self):
            return None

    class TurnFactory:
        def __init__(self) -> None:
            self.turn = Turn()

        def create(self, **_kwargs):
            return self.turn, False

    turn_factory = TurnFactory()
    completion = RecordingCompletion()
    orchestrator = _orchestrator(turn_factory, completion, RecordingCache())

    events = orchestrator.events(_context())
    assert (await anext(events)).type == "text_chunk"
    await turn_factory.turn.started.wait()
    await events.aclose()

    assert turn_factory.turn.closed is True
    assert completion.kwargs is None


@pytest.mark.asyncio
async def test_orchestrator_binds_cache_write_to_answer_sources_and_request_epoch() -> None:
    class Turn:
        def __init__(self) -> None:
            self.answer_buffer = SimpleNamespace(full_answer="")
            self.llm_finish_reason = "stop"
            self.llm_usage = SimpleNamespace(
                prompt_tokens=2, completion_tokens=3, total_tokens=5, cached_tokens=0
            )

        async def events(self):
            self.answer_buffer.full_answer = "基于证据的回答"
            yield StreamEvent("text_chunk", {"token": "基于证据的回答"})

        async def check_generation_result(self):
            return None

    class TurnFactory:
        def __init__(self) -> None:
            self.turn = Turn()

        def create(self, **_kwargs):
            return self.turn, False

    context = _context()
    turn_factory = TurnFactory()
    completion = RecordingCompletion()
    cache = RecordingCache()
    orchestrator = _orchestrator(turn_factory, completion, cache)

    events = [event async for event in orchestrator.events(context)]

    assert [event.type for event in events] == ["text_chunk", "text", "done"]
    assert cache.writes == [
        ((context.cache_key, "基于证据的回答", context.sources), {"epoch": context.expected_epoch})
    ]
