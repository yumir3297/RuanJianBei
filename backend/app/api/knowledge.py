from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.core.deps import get_db_session
from app.core.exceptions import AppError, NotFoundError
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.knowledge_generation import KnowledgeGenerationRepository
from app.repositories.qa_cache import QACacheRepository
from app.services.data_import.chunker import KnowledgeChunker
from app.schemas.common import MessageResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead, KnowledgeUpdate


router = APIRouter(dependencies=[Depends(require_admin_token)])


async def _refresh_search_data(session: AsyncSession, entry) -> None:
    try:
        chunks = KnowledgeChunker().build_chunks([entry])
        await KnowledgeChunkRepository(session).replace_for_entry(entry.id, chunks)
    except Exception as exc:
        raise AppError(
            "知识已保留原版本；切块准备失败，请检查内容后重试。",
            error_code="knowledge_chunk_prepare_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    try:
        await QACacheRepository(session).invalidate(commit=False)
        await KnowledgeGenerationRepository(session).bump()
    except Exception as exc:
        raise AppError(
            "知识检索数据暂未发布；答案缓存失效步骤失败，请稍后重试。",
            error_code="knowledge_cache_invalidation_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


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
async def list_knowledge(session: AsyncSession = Depends(get_db_session)) -> list[KnowledgeRead]:
    repository = KnowledgeRepository(session)
    entries = await repository.list_all()
    return [_to_knowledge_read(entry) for entry in entries]


@router.post("/", response_model=KnowledgeRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge(payload: KnowledgeCreate, session: AsyncSession = Depends(get_db_session)) -> KnowledgeRead:
    repository = KnowledgeRepository(session)
    try:
        entry = await repository.create(payload, commit=False)
        await _refresh_search_data(session, entry)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if isinstance(exc, AppError):
            raise
        raise AppError(
            "知识写入事务失败；原有游客可见内容保持不变，请重试。",
            error_code="knowledge_write_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return _to_knowledge_read(entry)


@router.put("/{knowledge_id}", response_model=KnowledgeRead)
async def update_knowledge(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRead:
    repository = KnowledgeRepository(session)
    entry = await repository.get(knowledge_id)
    if entry is None:
        raise NotFoundError("Knowledge entry not found.")
    try:
        updated = await repository.update(entry, payload, commit=False)
        await _refresh_search_data(session, updated)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if isinstance(exc, AppError):
            raise
        raise AppError(
            "知识更新事务失败；原有游客可见内容保持不变，请重试。",
            error_code="knowledge_write_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return _to_knowledge_read(updated)


@router.delete("/{knowledge_id}", response_model=MessageResponse)
async def delete_knowledge(knowledge_id: int, session: AsyncSession = Depends(get_db_session)) -> MessageResponse:
    repository = KnowledgeRepository(session)
    entry = await repository.get(knowledge_id)
    if entry is None:
        raise NotFoundError("Knowledge entry not found.")
    try:
        await KnowledgeChunkRepository(session).replace_for_entry(entry.id, [])
        await repository.delete(entry, commit=False)
        await QACacheRepository(session).invalidate(commit=False)
        await KnowledgeGenerationRepository(session).bump()
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise AppError(
            "知识下架未完成；原有游客可见内容保持不变，请重试。",
            error_code="knowledge_delete_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return MessageResponse(message="Knowledge entry deleted.")
