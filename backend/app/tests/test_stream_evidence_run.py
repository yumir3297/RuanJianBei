from __future__ import annotations

import asyncio

import pytest

from app.services.qa.stream_evidence_run import StreamEvidenceRun
from app.services.rag.base import RetrievedDocument, RetrievalScope


def test_faq_evidence_run_skips_rag_and_publishes_bound_sources_in_order() -> None:
    class ForbiddenRag:
        async def retrieve(self, *_args, **_kwargs):
            raise AssertionError("FAQ evidence must not fall through to RAG")

    async def scenario():
        run = StreamEvidenceRun(
            rag_service=ForbiddenRag(),
            query="景区在哪里",
            normalized_query="景区在哪里",
            scope=None,
            faq_documents=[RetrievedDocument(
                title="FAQ", content="灵山胜境位于无锡马山。",
                snippet="灵山胜境位于无锡马山。", source="景区官方公告", score=1.0,
            )],
            faq_sources=[{"evidence_id": "证据1", "source": "景区官方公告"}],
            epoch_is_current=lambda: asyncio.sleep(0, result=True),
        )

        events = [event async for event in run.events()]

        assert [event.type for event in events] == ["status", "sources"]
        assert run.outcome is not None
        assert run.outcome.documents[0].title == "FAQ"
        assert run.outcome.sources == [{"evidence_id": "证据1", "source": "景区官方公告"}]

    asyncio.run(scenario())


def test_rag_evidence_run_preserves_scope_and_source_revision_binding() -> None:
    scope = RetrievalScope(source_entry_id=17)

    class RecordingRag:
        def __init__(self):
            self.call = None

        async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
            self.call = (query, normalized_query, scope)
            return [RetrievedDocument(
                title="灵山大佛", content="景点位于无锡马山。",
                snippet="景点位于无锡马山。", source="已发布知识库", score=0.91,
                entry_id=17, revision_id="rev-2026-11", chunk_id="chunk-4",
            )]

    async def scenario():
        rag = RecordingRag()
        run = StreamEvidenceRun(
            rag_service=rag,
            query="景点在哪",
            normalized_query="灵山大佛在哪里",
            scope=scope,
            faq_documents=None,
            faq_sources=[],
            epoch_is_current=lambda: asyncio.sleep(0, result=True),
        )

        events = [event async for event in run.events()]

        assert rag.call == ("景点在哪", "灵山大佛在哪里", scope)
        assert [event.type for event in events] == ["status", "sources"]
        assert run.outcome is not None
        assert run.outcome.documents[0].chunk_id == "chunk-4"
        assert run.outcome.sources[0]["revision_id"] == "rev-2026-11"
        assert run.outcome.sources[0]["chunk_id"] == "chunk-4"
        assert events[-1].data["docs"] == run.outcome.sources

    asyncio.run(scenario())


def test_stale_epoch_after_retrieval_does_not_publish_sources_or_return_evidence() -> None:
    class RecordingRag:
        async def retrieve(self, *_args, **_kwargs):
            return [RetrievedDocument(
                title="隐藏条目", content="过期内容", snippet="过期内容",
                source="已发布知识库", score=0.9,
            )]

    async def scenario():
        checks = 0

        async def epoch_is_current():
            nonlocal checks
            checks += 1
            return False

        run = StreamEvidenceRun(
            rag_service=RecordingRag(),
            query="查询",
            normalized_query="查询",
            scope=None,
            faq_documents=None,
            faq_sources=[],
            epoch_is_current=epoch_is_current,
        )

        events = [event async for event in run.events()]

        assert [event.type for event in events] == ["status", "error"]
        assert run.outcome is not None
        assert run.outcome.error_event is not None
        assert run.outcome.documents == []
        assert checks == 1

    asyncio.run(scenario())


def test_epoch_change_while_source_event_is_delivered_stops_before_evidence_use() -> None:
    class RecordingRag:
        async def retrieve(self, *_args, **_kwargs):
            return [RetrievedDocument(
                title="可见条目", content="片段", snippet="片段",
                source="已发布知识库", score=0.9,
            )]

    async def scenario():
        checks = 0

        async def epoch_is_current():
            nonlocal checks
            checks += 1
            return checks == 1

        run = StreamEvidenceRun(
            rag_service=RecordingRag(),
            query="查询",
            normalized_query="查询",
            scope=None,
            faq_documents=None,
            faq_sources=[],
            epoch_is_current=epoch_is_current,
        )

        events = [event async for event in run.events()]

        assert [event.type for event in events] == ["status", "sources", "error"]
        assert run.outcome is not None
        assert run.outcome.error_event is not None
        assert run.outcome.documents == []
        assert checks == 2

    asyncio.run(scenario())


def test_cancelling_evidence_stream_closes_inflight_retrieval() -> None:
    class BlockingRag:
        def __init__(self):
            self.started = asyncio.Event()
            self.closed = asyncio.Event()

        async def retrieve(self, *_args, **_kwargs):
            self.started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.closed.set()

    async def scenario():
        rag = BlockingRag()
        run = StreamEvidenceRun(
            rag_service=rag,
            query="查询",
            normalized_query="查询",
            scope=None,
            faq_documents=None,
            faq_sources=[],
            epoch_is_current=lambda: asyncio.sleep(0, result=True),
        )
        events = run.events()
        assert (await anext(events)).type == "status"
        pending = asyncio.create_task(anext(events))
        await rag.started.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        await events.aclose()

        assert rag.closed.is_set()
        assert run.outcome is None

    asyncio.run(scenario())
