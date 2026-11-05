from __future__ import annotations

import unittest

from app.services.qa.stream_events import StreamEvent
from app.services.qa.fast_path_answer_coordinator import FastPathAnswerCoordinator


class FastPathAnswerCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_answer_and_speech_events_precede_persist_and_terminal_events(self):
        order = []

        class Speech:
            async def render(self, **kwargs):
                order.append("speech")
                return [StreamEvent(type="avatar"), StreamEvent(type="audio")]

        async def epoch_is_current(expected_epoch):
            order.append("epoch")
            return True

        def prepare(answer, sources):
            order.append("prepare")
            return f"{answer}[evidence]"

        async def persist(answer, latency_ms):
            order.append(("persist", answer))
            return 37

        coordinator = FastPathAnswerCoordinator(
            speech_emitter=Speech(), epoch_is_current=epoch_is_current
        )
        events = [event async for event in coordinator.events(
            answer="答案", sources=[{"id": 1}], hit_level="rag", text_only=False,
            expected_epoch=9, start=0.0, prepare_answer=prepare,
            persist_answer=persist,
            followups_event=lambda: (order.append("followups") or StreamEvent(type="followups")),
            done_event=lambda chat_log_id, latency_ms: (
                order.append("done") or StreamEvent(type="done", data={"id": chat_log_id})
            ),
        )]

        self.assertEqual([event.type for event in events], ["sources", "text", "avatar", "audio", "followups", "done"])
        self.assertEqual(order[:5], ["epoch", "prepare", "epoch", "speech", ("persist", "答案[evidence]")])
        self.assertEqual(order[5:], ["followups", "done"])

    async def test_epoch_change_after_sources_stops_before_text_and_persistence(self):
        checks = iter([True, False])
        calls = []

        class Speech:
            async def render(self, **kwargs):
                calls.append("speech")
                return []

        async def epoch_is_current(expected_epoch):
            return next(checks)

        coordinator = FastPathAnswerCoordinator(
            speech_emitter=Speech(), epoch_is_current=epoch_is_current
        )
        events = [event async for event in coordinator.events(
            answer="答案", sources=[{"id": 1}], hit_level="faq_direct", text_only=True,
            expected_epoch=4, start=0.0,
            prepare_answer=lambda answer, sources: calls.append("prepare") or answer,
            persist_answer=lambda *_: calls.append("persist"),
            followups_event=lambda: StreamEvent(type="followups"),
            done_event=lambda *_: StreamEvent(type="done"),
        )]

        self.assertEqual([event.type for event in events], ["sources", "error"])
        self.assertEqual(calls, ["prepare"])

    async def test_speech_epoch_error_does_not_persist_answer(self):
        calls = []

        class Speech:
            async def render(self, **kwargs):
                return [StreamEvent(type="error", data={"message": "stale"})]

        async def epoch_is_current(expected_epoch):
            return True

        coordinator = FastPathAnswerCoordinator(
            speech_emitter=Speech(), epoch_is_current=epoch_is_current
        )
        events = [event async for event in coordinator.events(
            answer="答案", sources=[], hit_level="faq_direct", text_only=False,
            expected_epoch=4, start=0.0,
            prepare_answer=lambda answer, sources: answer,
            persist_answer=lambda *_: calls.append("persist"),
            followups_event=lambda: StreamEvent(type="followups"),
            done_event=lambda *_: StreamEvent(type="done"),
        )]

        self.assertEqual([event.type for event in events], ["text", "error"])
        self.assertEqual(calls, [])

    async def test_text_only_answer_skips_speech_and_still_completes(self):
        calls = []

        class Speech:
            async def render(self, **kwargs):
                raise AssertionError("text-only answer must not synthesize speech")

        async def epoch_is_current(expected_epoch):
            return True

        async def persist(answer, latency_ms):
            calls.append(("persist", answer))
            return 11

        coordinator = FastPathAnswerCoordinator(
            speech_emitter=Speech(), epoch_is_current=epoch_is_current
        )
        events = [event async for event in coordinator.events(
            answer="文字答案", sources=[], hit_level="faq_direct", text_only=True,
            expected_epoch=3, start=0.0,
            prepare_answer=lambda answer, sources: answer,
            persist_answer=persist,
            followups_event=lambda: StreamEvent(type="followups"),
            done_event=lambda chat_log_id, latency_ms: StreamEvent(
                type="done", data={"chat_log_id": chat_log_id}
            ),
        )]

        self.assertEqual([event.type for event in events], ["text", "followups", "done"])
        self.assertEqual(events[-1].data, {"chat_log_id": 11})
        self.assertEqual(calls, [("persist", "文字答案")])


if __name__ == "__main__":
    unittest.main()
