from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_workspace import KnowledgeWorkspaceRepository
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.schemas.common import MessageResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead, KnowledgeUpdate
from app.services.knowledge.understanding_preview import PreviewRequest, preview_understanding
from app.core.exceptions import AppError, NotFoundError
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, SourceDocumentVersion
from app.services.knowledge.file_storage import KnowledgeFileStorage


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
        source_document_version_id=revision.source_document_version_id if revision else None,
        page_start=revision.page_start if revision else None,
        page_end=revision.page_end if revision else None,
        section_path=revision.section_path if revision else None,
    )


@router.get("/", response_model=list[KnowledgeRead])
async def list_knowledge(session: AsyncSession = Depends(get_db_session)) -> list[KnowledgeRead]:
    repository = KnowledgeRepository(session)
    entries = await repository.list_all()
    workspace = KnowledgeWorkspaceRepository(session)
    result = []
    for entry in entries:
        revision_id = entry.draft_revision_id or entry.published_revision_id
        revision = await workspace.get_revision(revision_id) if revision_id else None
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


@router.post("/{knowledge_id}/understanding-preview")
async def understanding_preview(
    knowledge_id: int, payload: PreviewRequest,
    session: AsyncSession = Depends(get_db_session), settings: Settings = Depends(get_app_settings),
) -> dict:
    return await preview_understanding(session, settings, knowledge_id, payload)


@router.get("/{knowledge_id}/source")
async def download_source(
    knowledge_id: int, revision_id: str = Query(min_length=1, max_length=36),
    session: AsyncSession = Depends(get_db_session), settings: Settings = Depends(get_app_settings),
) -> FileResponse:
    entry = await session.get(KnowledgeEntry, knowledge_id)
    if entry is None:
        raise NotFoundError("Knowledge entry not found.")
    if revision_id != (entry.draft_revision_id or entry.published_revision_id):
        raise AppError("知识版本已变化，请刷新后重试。", error_code="knowledge_version_conflict", status_code=409)
    revision = await session.get(KnowledgeRevision, revision_id)
    if revision is None or revision.knowledge_entry_id != entry.id or not revision.source_document_version_id:
        raise NotFoundError("Source document not found.")
    version = await session.get(SourceDocumentVersion, revision.source_document_version_id)
    if version is None:
        raise NotFoundError("Source document not found.")
    root = settings.knowledge_upload_root.resolve()
    path = (root / version.storage_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise NotFoundError("Source document not found.")
    return FileResponse(path, media_type=version.mime_type, filename=KnowledgeFileStorage._display_filename(version.original_filename),
                        content_disposition_type="attachment", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


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
