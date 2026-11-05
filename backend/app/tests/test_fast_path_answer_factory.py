import asyncio
from types import SimpleNamespace

from app.services.emotion import MultimodalEmotionFusion, response_policy_for
from app.services.qa.fast_path_answer_factory import FastPathAnswerFactory
from app.services.qa.stream_events import StreamEvent


class RecordingCoordinator:
    def __init__(self):
        self.kwargs = None

    def events(self, **kwargs):
        self.kwargs = kwargs

        async def source():
            yield StreamEvent(type="text", data={"text": kwargs["prepare_answer"](kwargs["answer"], kwargs["sources"])})

        return source()


def test_factory_binds_personalized_answer_persistence_and_terminal_metadata():
    async def scenario():
        calls = []
        coordinator = RecordingCoordinator()
        response_policy = response_policy_for(MultimodalEmotionFusion().fuse(None, None))
        request = SimpleNamespace(session_id="session-1", query="原问题", text_only=True)
        resolved = SimpleNamespace(active_subject="灵山大佛")

        async def persist(**kwargs):
            calls.append(("persist", kwargs))
            return 23

        factory = FastPathAnswerFactory(
            coordinator=coordinator,
            citation_binder=lambda answer, sources: f"{answer}[{sources[0]['evidence_id']}]",
            persist_interaction=persist,
            done_event_builder=lambda **kwargs: StreamEvent(type="done", data=kwargs),
            followup_event_builder=lambda resolved: StreamEvent(
                type="followups", data={"subject": resolved.active_subject}
            ),
        )

        events = [event async for event in factory.events(
            request=request,
            normalized_query="规范问题",
            answer="回答",
            sources=[{"evidence_id": "证据1"}],
            hit_level="faq_direct",
            start=1.5,
            resolved=resolved,
            response_policy=response_policy,
            expected_epoch=8,
        )]

        assert events[0].data["text"].endswith("回答[证据1]")
        assert coordinator.kwargs["expected_epoch"] == 8
        assert coordinator.kwargs["text_only"] is True
        assert coordinator.kwargs["done_event"](23, 7).data == {
            "chat_log_id": 23,
            "hit_level": "faq_direct",
            "total_ms": 7,
            "degraded": False,
            "provider": "local",
        }
        await coordinator.kwargs["persist_answer"]("最终回答", 7)
        assert calls == [("persist", {
            "session_id": "session-1",
            "raw_query": "原问题",
            "normalized_query": "规范问题",
            "answer": "最终回答",
            "sources": [{"evidence_id": "证据1"}],
            "hit_level": "faq_direct",
            "latency_ms": 7,
            "request": request,
            "active_subject": "灵山大佛",
        })]

    asyncio.run(scenario())
