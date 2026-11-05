from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services.qa.stream_answer_completion_factory import StreamAnswerCompletionFactory
from app.services.qa.stream_events import StreamEvent


class RecordingCompletion:
    def __init__(self):
        self.kwargs = None

    def events(self, **kwargs):
        self.kwargs = kwargs

        async def source():
            if False:
                yield None

        return source()


def _outcome(*, should_cache: bool, degraded: bool):
    policy = SimpleNamespace(
        should_cache=should_cache,
        hit_level="faq_exact_styled_llm_fallback" if degraded else "faq_exact_styled",
        degraded=degraded,
        provider="primary",
        completion="incomplete" if degraded else "complete",
        incomplete=degraded,
    )
    stream_turn = SimpleNamespace(
        answer_buffer=SimpleNamespace(full_answer="生成中间答案"),
        llm_usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=4,
            total_tokens=14,
            cached_tokens=0,
        ),
        llm_finish_reason="fallback_provider_error" if degraded else "stop",
    )
    finalized = SimpleNamespace(answer="最终规范答案", policy=policy)
    return SimpleNamespace(
        stream_turn=stream_turn,
        streaming_requested=True,
        finalized=finalized,
    )


def _factory(completion, *, tracker=None, events=None):
    request = SimpleNamespace(session_id="s-1", query="游客原问题")
    return StreamAnswerCompletionFactory(
        completion=completion,
        cache_writer=lambda *args: async_record(events, "cache", *args),
        persist_interaction=lambda **kwargs: async_result(events, "persist", kwargs, "log-1"),
        blind_spot_tracker=tracker,
        request=request,
        normalized_query="规范问题",
        sources=[{"evidence_id": "证据1"}],
        expected_epoch=7,
        start=1.0,
        active_subject="灵山大佛",
        followup_event=lambda: StreamEvent("followups", {"items": ["下一问"]}),
        done_event_builder=lambda **kwargs: StreamEvent("done", kwargs),
        faq_documents_present=True,
        text_only=False,
        epoch_is_current=lambda: asyncio.sleep(0, result=True),
    )


def test_factory_binds_canonical_answer_and_only_enables_approved_cache() -> None:
    async def scenario():
        events = []
        completion = RecordingCompletion()
        outcome = _outcome(should_cache=True, degraded=False)
        factory = _factory(completion, events=events)

        completion_events = factory.build(outcome)

        assert outcome.stream_turn.answer_buffer.full_answer == "最终规范答案"
        assert completion.kwargs["answer"] == "最终规范答案"
        assert completion.kwargs["faq_text_sent"] is True
        assert completion.kwargs["faq_documents_present"] is True
        assert completion.kwargs["text_only"] is False
        assert completion.kwargs["streaming_requested"] is True
        assert completion.kwargs["cache_answer"] is not None
        await completion.kwargs["cache_answer"]()
        await completion.kwargs["persist_answer"]()

        assert events[0] == ("cache", "最终规范答案", [{"evidence_id": "证据1"}], 7)
        assert events[1][0] == "persist"
        assert events[1][1]["session_id"] == "s-1"
        assert events[1][1]["normalized_query"] == "规范问题"
        await completion_events.aclose()

    asyncio.run(scenario())


def test_factory_disables_degraded_cache_and_retains_fallback_recording() -> None:
    class RecordingTracker:
        def __init__(self):
            self.records = []

        async def record(self, **kwargs):
            self.records.append(kwargs)

    async def scenario():
        tracker = RecordingTracker()
        completion = RecordingCompletion()
        outcome = _outcome(should_cache=False, degraded=True)
        factory = _factory(completion, tracker=tracker)

        completion_events = factory.build(outcome)

        assert completion.kwargs["cache_answer"] is None
        await completion.kwargs["after_audio"]()
        assert tracker.records == [{
            "raw_query": "游客原问题",
            "normalized_query": "规范问题",
            "category": "llm_fallback",
        }]
        await completion_events.aclose()

    asyncio.run(scenario())


async def async_record(target, *values):
    target.append(values)


async def async_result(target, name, value, result):
    target.append((name, value))
    return result
