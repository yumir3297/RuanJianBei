import asyncio
from dataclasses import dataclass

from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import Reranker
from app.services.rag.retriever import RepositoryBackedRAGService
from app.services.rag.base import RetrievalScope


@dataclass(slots=True)
class FakeKnowledgeEntry:
    title: str
    content: str
    aliases: str
    source: str


class FakeKnowledgeRepository:
    def __init__(self, entries: list[FakeKnowledgeEntry]) -> None:
        self.entries = entries

    def search(self, query: str, limit: int = 10, *, knowledge_id=None, category=None) -> list[FakeKnowledgeEntry]:
        del query, limit, knowledge_id, category
        return self.entries


def test_repository_rag_preserves_full_content_for_future_reranker() -> None:
    full_content = "A" * 220 + " important tail evidence"
    service = RepositoryBackedRAGService(
        FakeKnowledgeRepository(
            [
                FakeKnowledgeEntry(
                    title="Scenic Spot",
                    content=full_content,
                    aliases="spot",
                    source="official_data_pack",
                )
            ]
        ),
        QueryRewriter(),
        Reranker(),
    )

    documents = asyncio.run(service.retrieve("spot", normalized_query="spot", top_k=1))

    assert len(documents) == 1
    assert documents[0].content == full_content
    assert documents[0].snippet == full_content[:160]
    assert "important tail evidence" in documents[0].content
    assert "important tail evidence" not in documents[0].snippet


class ScopedKnowledgeRepository(FakeKnowledgeRepository):
    def __init__(self, entries):
        super().__init__(entries)
        self.last_scope = None

    def search(self, query: str, limit: int = 10, *, knowledge_id=None, category=None):
        del query, limit
        self.last_scope = (knowledge_id, category)
        return self.entries


def test_repository_rag_passes_scope_to_database_search() -> None:
    repository = ScopedKnowledgeRepository(
        [FakeKnowledgeEntry(title="五印坛城", content="官方资料", aliases="坛城", source="official")]
    )
    service = RepositoryBackedRAGService(repository, QueryRewriter(), Reranker())

    asyncio.run(
        service.retrieve(
            "有什么特色",
            normalized_query="有什么特色",
            scope=RetrievalScope(source_entry_id=16, category="景点信息"),
        )
    )

    assert repository.last_scope == (16, "景点信息")
