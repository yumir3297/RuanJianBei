from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk


class KnowledgeChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[KnowledgeChunk]:
        stmt = select(KnowledgeChunk).order_by(KnowledgeChunk.source_entry_id.asc(), KnowledgeChunk.chunk_index.asc())
        return list(self.session.scalars(stmt))

    def replace_all(self, chunks: list[KnowledgeChunk]) -> int:
        self.session.execute(delete(KnowledgeChunk))
        self.session.add_all(chunks)
        self.session.flush()
        return len(chunks)

    def count(self) -> int:
        return self.session.scalar(select(func.count(KnowledgeChunk.chunk_id))) or 0
