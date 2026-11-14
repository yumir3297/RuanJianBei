from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.models.qa_cache import QACacheEntry
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate


class KnowledgeWorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_draft(
        self,
        entry_id: int | None,
        payload: KnowledgeCreate | KnowledgeUpdate,
        *,
        expected_version: int | None = None,
    ) -> tuple[KnowledgeEntry, KnowledgeRevision]:
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        if entry_id is None:
            if not isinstance(payload, KnowledgeCreate):
                raise AppError("A new knowledge entry needs title, content, and source.", error_code="invalid_draft")
            entry = KnowledgeEntry(
                title=payload.title,
                category=payload.category,
                content=payload.content,
                source=payload.source,
                aliases="|".join(payload.aliases),
                metadata_json=payload.metadata_json,
                lock_version=1,
            )
            self.session.add(entry)
            await self.session.flush()
            expected_version = entry.lock_version
        else:
            entry = await self.session.get(KnowledgeEntry, entry_id)
            if entry is None:
                raise NotFoundError("Knowledge entry not found.")
            if entry.withdrawn_at is not None:
                raise AppError("Withdrawn knowledge cannot be edited or restored by saving a draft.", error_code="knowledge_withdrawn", status_code=409)
            if expected_version is not None and expected_version != entry.lock_version:
                raise AppError("This knowledge entry changed. Reload it before saving.", error_code="knowledge_version_conflict", status_code=409)
            expected_version = entry.lock_version

        base_revision_id = entry.published_revision_id
        value_revision_id = entry.draft_revision_id or entry.published_revision_id
        base_revision = await self.session.get(KnowledgeRevision, value_revision_id) if value_revision_id else None
        values = {
            "title": base_revision.title if base_revision else entry.title,
            "category": base_revision.category if base_revision else entry.category,
            "content": base_revision.content if base_revision else entry.content,
            "source": base_revision.source if base_revision else entry.source,
            "aliases": base_revision.aliases if base_revision else entry.aliases,
            "metadata_json": base_revision.metadata_json if base_revision else entry.metadata_json,
        }
        for key, value in changes.items():
            if value is None and key != "metadata_json":
                continue
            values[key] = "|".join(value) if key == "aliases" and value is not None else value

        retain_origin = bool(base_revision and values["source"] == base_revision.source)
        if base_revision and base_revision.source_document_version_id and not retain_origin and values["metadata_json"]:
            try:
                metadata = json.loads(values["metadata_json"])
                if isinstance(metadata, dict):
                    for key in ("source_document_id", "sha256", "section_identity", "stable_id", "extraction_method"):
                        metadata.pop(key, None)
                    values["metadata_json"] = json.dumps(metadata, ensure_ascii=False)
                else:
                    values["metadata_json"] = None
            except (ValueError, TypeError):
                # Opaque metadata cannot safely carry prior source attribution.
                values["metadata_json"] = None
        revision = KnowledgeRevision(
            id=str(uuid4()),
            knowledge_entry_id=entry.id,
            base_revision_id=base_revision_id,
            title=values["title"],
            category=values["category"],
            content=values["content"],
            source=values["source"],
            aliases=values["aliases"] or "",
            metadata_json=values["metadata_json"],
            source_document_version_id=base_revision.source_document_version_id if retain_origin else None,
            page_start=base_revision.page_start if retain_origin else None,
            page_end=base_revision.page_end if retain_origin else None,
            section_path=base_revision.section_path if retain_origin else None,
        )
        self.session.add(revision)
        await self.session.flush()
        result = await self.session.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.id == entry.id, KnowledgeEntry.lock_version == expected_version)
            .values(draft_revision_id=revision.id, lock_version=KnowledgeEntry.lock_version + 1)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise AppError("This knowledge entry changed. Reload it before saving.", error_code="knowledge_version_conflict", status_code=409)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry, revision

    async def discard_draft(self, entry_id: int, *, expected_version: int | None = None) -> None:
        entry = await self.session.get(KnowledgeEntry, entry_id)
        if entry is None or entry.draft_revision_id is None:
            raise NotFoundError("Knowledge draft not found.")
        if expected_version is not None and expected_version != entry.lock_version:
            raise AppError("This knowledge entry changed. Reload it before discarding.", error_code="knowledge_version_conflict", status_code=409)

        result = await self.session.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.id == entry.id, KnowledgeEntry.lock_version == entry.lock_version)
            .values(draft_revision_id=None, lock_version=KnowledgeEntry.lock_version + 1)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise AppError("This knowledge entry changed. Reload it before discarding.", error_code="knowledge_version_conflict", status_code=409)
        if entry.published_revision_id is None:
            await self.session.execute(
                update(KnowledgeRevision)
                .where(KnowledgeRevision.knowledge_entry_id == entry.id)
                .values(base_revision_id=None)
            )
            await self.session.execute(delete(KnowledgeRevision).where(KnowledgeRevision.knowledge_entry_id == entry.id))
            await self.session.execute(delete(KnowledgeEntry).where(KnowledgeEntry.id == entry.id))
        await self.session.commit()

    async def withdraw(self, entry_id: int, *, expected_version: int | None = None) -> None:
        entry = await self.session.get(KnowledgeEntry, entry_id)
        if entry is None:
            raise NotFoundError("Knowledge entry not found.")
        if entry.withdrawn_at is not None:
            raise NotFoundError("Knowledge entry is already withdrawn.")
        if expected_version is not None and expected_version != entry.lock_version:
            raise AppError("This knowledge entry changed. Reload it before withdrawing.", error_code="knowledge_version_conflict", status_code=409)

        dialect = self.session.bind.dialect.name if self.session.bind is not None else ""
        if dialect == "sqlite":
            if await self.session.get(KnowledgeState, 1) is None:
                raise AppError("Knowledge state is unavailable; check database migrations.", error_code="knowledge_state_missing", status_code=409)
        else:
            result = await self.session.execute(
                update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch + 1)
            )
            if result.rowcount != 1:
                raise AppError("Knowledge state is unavailable; check database migrations.", error_code="knowledge_state_missing", status_code=409)
        result = await self.session.execute(
            update(KnowledgeEntry)
            .where(KnowledgeEntry.id == entry.id, KnowledgeEntry.lock_version == entry.lock_version)
            .values(
                published_revision_id=None,
                withdrawn_at=datetime.now(UTC),
                lock_version=KnowledgeEntry.lock_version + 1,
            )
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise AppError("This knowledge entry changed. Reload it before withdrawing.", error_code="knowledge_version_conflict", status_code=409)

        await self.session.execute(delete(QACacheEntry))
        if dialect == "sqlite":
            await self.session.execute(
                update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch + 1)
            )
        await self.session.commit()
