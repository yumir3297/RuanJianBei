from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.core.exceptions import NotFoundError
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.common import MessageResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead, KnowledgeUpdate


router = APIRouter()


def _to_knowledge_read(entry) -> KnowledgeRead:
    return KnowledgeRead(
        id=entry.id,
        title=entry.title,
        category=entry.category,
        content=entry.content,
        source=entry.source,
        aliases=[item for item in entry.aliases.split("|") if item],
        metadata_json=entry.metadata_json,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/", response_model=list[KnowledgeRead])
async def list_knowledge(session: Session = Depends(get_db_session)) -> list[KnowledgeRead]:
    repository = KnowledgeRepository(session)
    entries = repository.list_all()
    return [_to_knowledge_read(entry) for entry in entries]


@router.post("/", response_model=KnowledgeRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge(payload: KnowledgeCreate, session: Session = Depends(get_db_session)) -> KnowledgeRead:
    repository = KnowledgeRepository(session)
    entry = repository.create(payload)
    return _to_knowledge_read(entry)


@router.put("/{knowledge_id}", response_model=KnowledgeRead)
async def update_knowledge(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    session: Session = Depends(get_db_session),
) -> KnowledgeRead:
    repository = KnowledgeRepository(session)
    entry = repository.get(knowledge_id)
    if entry is None:
        raise NotFoundError("Knowledge entry not found.")
    updated = repository.update(entry, payload)
    return _to_knowledge_read(updated)


@router.delete("/{knowledge_id}", response_model=MessageResponse)
async def delete_knowledge(knowledge_id: int, session: Session = Depends(get_db_session)) -> MessageResponse:
    repository = KnowledgeRepository(session)
    entry = repository.get(knowledge_id)
    if entry is None:
        raise NotFoundError("Knowledge entry not found.")
    repository.delete(entry)
    return MessageResponse(message="Knowledge entry deleted.")
