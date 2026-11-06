import asyncio
from contextlib import aclosing
from types import SimpleNamespace

from app.services.qa.no_evidence_answer_handler import NoEvidenceAnswerHandler
from app.services.qa.stream_events import StreamEvent


class RecordingFastPathFactory:
    def __init__(self):
        self.kwargs = None
        self.closed = False

    def events(self, **kwargs):
        self.kwargs = kwargs

        async def source():
            try:
                yield StreamEvent(type="text", data={"text": "answer"})
                yield StreamEvent(type="done")
            finally:
                self.closed = True

        return source()


def test_blind_spot_failure_does_not_block_no_evidence_fast_answer(caplog):
    async def scenario():
        class FailingTracker:
            async def record(self, **kwargs):
                raise RuntimeError("tracker unavailable")

        fast_path = RecordingFastPathFactory()
        handler = NoEvidenceAnswerHandler(
            fast_path_answer_factory=fast_path,
            blind_spot_tracker=FailingTracker(),
        )
        request = SimpleNamespace(persona="adult", text_only=True)
        resolved = SimpleNamespace(active_subject=None)
        response_policy = object()
        events = [event async for event in handler.events(
            request=request,
            normalized_query="规范后的查询",
            start=2.5,
            resolved=resolved,
            response_policy=response_policy,
            expected_epoch=11,
        )]

        assert [event.type for event in events] == ["text", "done"]
        assert fast_path.kwargs["answer"]
        assert fast_path.kwargs["sources"] == []
        assert fast_path.kwargs["hit_level"] == "rag_insufficient"
        assert fast_path.kwargs["expected_epoch"] == 11
        assert fast_path.kwargs["response_policy"] is response_policy
        assert "Knowledge blind spot recording failed" in caplog.text

    asyncio.run(scenario())


def test_closing_no_evidence_handler_closes_fast_path_events():
    async def scenario():
        fast_path = RecordingFastPathFactory()
        handler = NoEvidenceAnswerHandler(fast_path_answer_factory=fast_path)
        events = handler.events(
            request=SimpleNamespace(persona="adult", text_only=True),
            normalized_query="query",
            start=1.0,
            resolved=SimpleNamespace(active_subject=None),
            response_policy=object(),
            expected_epoch=3,
        )

        async with aclosing(events):
            event = await anext(events)
            assert event.type == "text"

        assert fast_path.closed

    asyncio.run(scenario())
