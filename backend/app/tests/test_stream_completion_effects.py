import asyncio
from types import SimpleNamespace

from app.services.qa.stream_completion_effects import StreamCompletionEffects
from app.services.qa.stream_events import StreamEvent


def test_completion_effects_bind_cache_persistence_fallback_and_done_metadata():
    calls = []

    class BlindSpotTracker:
        async def record(self, **kwargs):
            calls.append(("blind_spot", kwargs))

    async def cache_writer(answer, sources, epoch):
        calls.append(("cache", answer, sources, epoch))

    async def persist_interaction(**kwargs):
        calls.append(("persist", kwargs))
        return "log-7"

    def done_event_builder(**kwargs):
        calls.append(("done", kwargs))
        return StreamEvent("done", kwargs)

    effects = StreamCompletionEffects(
        cache_writer=cache_writer,
        persist_interaction=persist_interaction,
        blind_spot_tracker=BlindSpotTracker(),
        request=SimpleNamespace(session_id="s1", query="q1"),
        normalized_query="q1-normalized",
        answer="answer",
        sources=[{"id": "source-1"}],
        hit_level="rag_fallback",
        expected_epoch=9,
        start=0,
        llm_usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3, cached_tokens=0),
        llm_finish_reason="fallback_provider_error",
        degraded=True,
        provider="evidence_fallback",
        completion="complete",
        active_subject="spot-1",
        followup_event=lambda: StreamEvent("followups", {}),
        done_event_builder=done_event_builder,
    )

    async def run():
        await effects.cache_answer()
        chat_log_id = await effects.persist_answer()
        await effects.after_audio()
        return effects.done_event(chat_log_id)

    done = asyncio.run(run())

    assert [call[0] for call in calls] == ["cache", "persist", "blind_spot", "done"]
    assert calls[0] == ("cache", "answer", [{"id": "source-1"}], 9)
    assert calls[1][1]["active_subject"] == "spot-1"
    assert calls[1][1]["hit_level"] == "rag_fallback"
    assert calls[2][1]["category"] == "llm_fallback"
    assert done.type == "done"
    assert calls[3][1]["chat_log_id"] == "log-7"
    assert calls[3][1]["provider"] == "evidence_fallback"
