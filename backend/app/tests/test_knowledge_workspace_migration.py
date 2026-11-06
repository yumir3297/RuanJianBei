from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]


def _upgrade(database_url: str, revision: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    import os

    os.environ["DATABASE_URL"] = database_url
    command.upgrade(config, revision)


def test_existing_knowledge_and_chunks_migrate_as_published_revision(tmp_path, monkeypatch) -> None:
    database_url = os.environ.get("KNOWLEDGE_MIGRATION_TEST_URL") or f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    _upgrade(database_url, "a1c7f2d9b4e0")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO knowledge_entries
                    (id, title, category, content, source, aliases, metadata_json, created_at, updated_at)
                VALUES (47, '灵山大佛', '景点信息', '原有正式讲解', '导览手册', '', NULL,
                    '2026-01-01 00:00:00', '2026-01-01 00:00:00')
            """)
        )
        connection.execute(
            text("""
                INSERT INTO knowledge_chunks
                    (chunk_id, source_entry_id, chunk_index, title, category, content, source,
                     metadata_json, created_at)
                VALUES ('ke_47_001', 47, 1, '灵山大佛', '景点信息', '原有切块', '导览手册', NULL,
                    '2026-01-01 00:00:00')
            """)
        )

    _upgrade(database_url, "head")
    with engine.connect() as connection:
        entry = connection.execute(
            text("SELECT id, content, published_revision_id, draft_revision_id, lock_version FROM knowledge_entries")
        ).one()
        revision = connection.execute(
            text("SELECT id, content FROM knowledge_revisions WHERE knowledge_entry_id = 47")
        ).one()
        chunk = connection.execute(text("SELECT revision_id FROM knowledge_chunks WHERE chunk_id = 'ke_47_001'")).one()

    assert entry.id == 47
    assert entry.content == "原有正式讲解"
    assert entry.published_revision_id == revision.id
    assert entry.draft_revision_id is None
    assert entry.lock_version >= 1
    assert revision.content == "原有正式讲解"
    assert chunk.revision_id == revision.id
    engine.dispose()


def test_alembic_migration_keeps_qa_loggers_enabled(tmp_path, monkeypatch) -> None:
    from app.services.qa.no_evidence_answer_handler import logger as qa_logger

    database_url = f"sqlite:///{tmp_path / 'logger-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    qa_logger.disabled = False

    _upgrade(database_url, "head")

    assert qa_logger.disabled is False


def test_draft_revision_survives_database_session_recreation(tmp_path) -> None:
    import asyncio

    from sqlalchemy import select

    from app.models.knowledge import KnowledgeEntry
    from app.models.knowledge_workspace import KnowledgeRevision
    from app.tests.async_db import open_test_session

    async def scenario() -> None:
        database_path = str(tmp_path / "workspace.db")
        engine, session = await open_test_session(database_path)
        entry = KnowledgeEntry(title="新条目", category="景点信息", content="占位", source="测试", aliases="")
        session.add(entry)
        await session.flush()
        revision = KnowledgeRevision(
            id="draft-revision-1",
            knowledge_entry_id=entry.id,
            title="新条目",
            category="景点信息",
            content="永久保留的草稿",
            source="测试 PDF 第 2 页",
            aliases="",
            created_at=None,
        )
        session.add(revision)
        await session.flush()
        entry.draft_revision_id = revision.id
        await session.commit()
        await session.close()
        await engine.dispose()

        engine, session = await open_test_session(database_path)
        restored = (await session.execute(select(KnowledgeEntry))).scalar_one()
        assert restored.draft_revision_id == "draft-revision-1"
        draft = await session.get(KnowledgeRevision, restored.draft_revision_id)
        assert draft is not None
        assert draft.content == "永久保留的草稿"
        assert draft.source == "测试 PDF 第 2 页"
        await session.close()
        await engine.dispose()

    asyncio.run(scenario())
