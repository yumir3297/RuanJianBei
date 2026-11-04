import asyncio

from app.services.rag.base import RetrievedDocument, RetrievalScope
from app.services.qa.evidence_retrieval import retrieve_evidence


def test_rag_evidence_keeps_scope_and_binds_source_ids_to_retrieved_chunks():
    class RecordingRag:
        def __init__(self):
            self.call = None

        async def retrieve(self, query, normalized_query=None, top_k=5, scope=None):
            self.call = (query, normalized_query, scope)
            return [
                RetrievedDocument(
                    title="灵山大佛",
                    snippet="景点位于无锡马山。",
                    source="已发布知识库",
                    score=0.91,
                    entry_id=17,
                    revision_id="rev-2026-11",
                    chunk_id="chunk-4",
                )
            ]

    rag = RecordingRag()
    scope = RetrievalScope(source_entry_id=17)
    result = asyncio.run(retrieve_evidence(
        rag,
        query="景点在哪",
        normalized_query="灵山大佛在哪里",
        scope=scope,
    ))

    assert rag.call == ("景点在哪", "灵山大佛在哪里", scope)
    assert result.documents[0].chunk_id == "chunk-4"
    assert result.sources == [{
        "evidence_id": "证据1",
        "title": "灵山大佛",
        "snippet": "景点位于无锡马山。",
        "source": "已发布知识库",
        "score": 0.91,
        "entry_id": 17,
        "revision_id": "rev-2026-11",
        "chunk_id": "chunk-4",
    }]
