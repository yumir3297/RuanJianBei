from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.deps import get_db_session
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_workspace import KnowledgeWorkspaceRepository
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.schemas.common import MessageResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead, KnowledgeUpdate


router = APIRouter(dependencies=[Depends(require_admin_token)])


def _to_knowledge_read(entry, revision=None) -> KnowledgeRead:
    return KnowledgeRead(
        id=entry.id,
        title=revision.title if revision else entry.title,
        category=revision.category if revision else entry.category,
        content=revision.content if revision else entry.content,
        source=revision.source if revision else entry.source,
        aliases=[item for item in (revision.aliases if revision else entry.aliases).split("|") if item],
        metadata_json=revision.metadata_json if revision else entry.metadata_json,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        published_revision_id=entry.published_revision_id,
        draft_revision_id=entry.draft_revision_id,
        lock_version=entry.lock_version,
        withdrawn_at=entry.withdrawn_at,
    )


@router.get("/", response_model=list[KnowledgeRead])
async def list_knowledge(session: AsyncSession = Depends(get_db_session)) -> list[KnowledgeRead]:
    repository = KnowledgeRepository(session)
    entries = await repository.list_all()
    workspace = KnowledgeWorkspaceRepository(session)
    result = []
    for entry in entries:
        revision = await workspace.get_revision(entry.draft_revision_id or entry.published_revision_id)
        result.append(_to_knowledge_read(entry, revision))
    return result


@router.post("/", response_model=KnowledgeRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge(payload: KnowledgeCreate, session: AsyncSession = Depends(get_db_session)) -> KnowledgeRead:
    entry, revision = await KnowledgeWorkspaceService(session).save_draft(None, payload)
    return _to_knowledge_read(entry, revision)


@router.put("/{knowledge_id}", response_model=KnowledgeRead)
async def update_knowledge(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRead:
    entry, revision = await KnowledgeWorkspaceService(session).save_draft(
        knowledge_id,
        payload,
        expected_version=payload.expected_version,
    )
    return _to_knowledge_read(entry, revision)


@router.delete("/{knowledge_id}", response_model=MessageResponse)
async def delete_knowledge(knowledge_id: int, session: AsyncSession = Depends(get_db_session)) -> MessageResponse:
    await KnowledgeWorkspaceService(session).withdraw(knowledge_id)
    return MessageResponse(message="Knowledge entry deleted.")


@router.delete("/{knowledge_id}/draft", response_model=MessageResponse)
async def discard_knowledge_draft(
    knowledge_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    await KnowledgeWorkspaceService(session).discard_draft(knowledge_id)
    return MessageResponse(message="Knowledge draft discarded.")
