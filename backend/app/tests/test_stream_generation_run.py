import asyncio
from types import SimpleNamespace

from app.services.qa.stream_events import StreamEvent
from app.services.qa.stream_generation_run import StreamGenerationRun


def test_generation_run_forwards_events_and_finalizes_the_canonical_faq_answer():
    class Turn:
        def __init__(self):
            self.answer_buffer = SimpleNamespace(full_answer="生成器返回的文本")
            self.llm_finish_reason = "fallback_provider_error"
            self.llm_usage = object()
            self.closed = False

        async def events(self):
            try:
                yield StreamEvent("text_chunk", {"text": "生成器返回的文本"})
            finally:
                self.closed = True

        async def check_generation_result(self):
            return None

    turn = Turn()
    factory = SimpleNamespace(create=lambda **_: (turn, False))
    run = StreamGenerationRun(
        turn_factory=factory,
        turn_kwargs={},
        finalization_kwargs={
            "faq_documents_present": True,
            "cache_allowed": True,
            "llm_hit_level": "faq_exact_styled",
            "fallback_hit_level": "faq_exact_styled_llm_fallback",
            "llm_provider": "primary",
            "faq_answer": "权威 FAQ 答案",
            "persona": "adult",
            "faq_sources": [],
        },
    )

    async def collect():
        return [event async for event in run.events()]

    events = asyncio.run(collect())

    assert [event.type for event in events] == ["text_chunk"]
    assert turn.closed is True
    assert run.outcome.stream_turn is turn
    assert run.outcome.streaming_requested is False
    assert run.outcome.error_event is None
    assert run.outcome.finalized.answer != "生成器返回的文本"
    assert run.outcome.finalized.policy.should_cache is False


def test_generation_run_preserves_generation_error_without_finalizing():
    error = StreamEvent("error", {"message": "知识内容已更新，请重新提问。"})
    turn = SimpleNamespace(
        answer_buffer=SimpleNamespace(full_answer="部分文本"),
        llm_finish_reason="stop",
        llm_usage=object(),
        events=lambda: empty_events(),
        check_generation_result=lambda: asyncio.sleep(0, result=error),
    )
    run = StreamGenerationRun(
        turn_factory=SimpleNamespace(create=lambda **_: (turn, False)),
        turn_kwargs={},
        finalization_kwargs={},
    )

    asyncio.run(anext(run.events(), None))

    assert run.outcome.error_event is error
    assert run.outcome.finalized is None


async def empty_events():
    if False:
        yield None
