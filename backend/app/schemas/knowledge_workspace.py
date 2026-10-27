from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeRevisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    metadata_json: str | None = None
    base_revision_id: str | None = None
    source_document_version_id: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_path: str | None = None


class KnowledgeRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_entry_id: int
    title: str
    category: str
    content: str
    source: str
    aliases: list[str]
    metadata_json: str | None
    created_at: datetime


class WorkspaceEntry(BaseModel):
    id: int
    published_revision_id: str | None
    draft_revision_id: str | None
    lock_version: int
    withdrawn_at: datetime | None


class ImportBatchRead(BaseModel):
    id: str
    state: str
    stage: str
    error: str | None = None


class PublicationRead(BaseModel):
    id: str
    state: str
    error: str | None = None
