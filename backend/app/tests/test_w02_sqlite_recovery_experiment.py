"""Synthetic SQLite experiment, not an automated repair or production migration."""
from pathlib import Path
import shutil

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, text

ROOT = Path(__file__).resolve().parents[2]


def test_experimental_native_alter_preserves_knowledge_with_foreign_keys(tmp_path, monkeypatch):
    scripts = tmp_path / "legacy_alembic"
    shutil.copytree(ROOT / "alembic", scripts, ignore=shutil.ignore_patterns("__pycache__"))
    migration = scripts / "versions" / "f1b4c9d76e20_add_tool_execution.py"
    source = migration.read_text().replace('down_revision: Union[str, None] = "8ab42c17d3e9"', 'down_revision: Union[str, None] = "e9f4c2b8016a"')
    source = "\n".join(line for line in source.split("\n") if not (
        'op.add_column("itinerary_proposals"' in line
        or 'op.create_index("ix_itinerary_proposals_execution_job_id"' in line
        or 'op.drop_index("ix_itinerary_proposals_execution_job_id"' in line
        or 'op.drop_column("itinerary_proposals"' in line
    ))
    migration.write_text(source)
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(scripts))
    command.upgrade(config, "f1b4c9d76e20")
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        connection.execute(text("INSERT INTO knowledge_entries (id,title,category,content,source,aliases,created_at,updated_at) VALUES (47,'test','test','original','test','',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO knowledge_chunks (chunk_id,source_entry_id,chunk_index,title,category,content,source,created_at) VALUES ('c47',47,0,'test','test','chunk','test',CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO qa_cache_entries (normalized_query,answer,sources,expires_at,created_at) VALUES ('q','a','[]','2099-01-01',CURRENT_TIMESTAMP)"))
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        path = ROOT / "alembic/versions/c84d0f1a7b92_add_knowledge_workspace.py"
        source = path.read_text()
        start = source.index('    with op.batch_alter_table("knowledge_entries")')
        end = source.index('    op.create_index("ix_knowledge_chunks_revision_id"', start)
        experimental = '''    op.execute("ALTER TABLE knowledge_entries ADD COLUMN published_revision_id VARCHAR(36) REFERENCES knowledge_revisions(id)")
    op.execute("ALTER TABLE knowledge_entries ADD COLUMN draft_revision_id VARCHAR(36) REFERENCES knowledge_revisions(id)")
    op.add_column("knowledge_entries", sa.Column("lock_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("knowledge_entries", sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN revision_id VARCHAR(36) REFERENCES knowledge_revisions(id)")
'''
        namespace = {}
        exec(compile(source[:start] + experimental + source[end:], str(path), "exec"), namespace)
        # Preserve the synthetic old data before testing a failure in the DDL transaction.
        connection.commit()
        connection.exec_driver_sql("BEGIN")
        assert connection.connection.driver_connection.in_transaction
        with Operations.context(MigrationContext.configure(connection)):
            namespace["upgrade"]()
        connection.rollback()  # Simulated failure immediately after c84 completes.
        assert connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='knowledge_revisions'").all() == []
        assert connection.execute(text("SELECT content FROM knowledge_entries")).scalar_one() == "original"
        assert connection.execute(text("SELECT content FROM knowledge_chunks")).scalar_one() == "chunk"
        assert connection.execute(text("SELECT count(*) FROM qa_cache_entries")).scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        connection.commit()  # Close the implicit read transaction before retrying.
        connection.exec_driver_sql("BEGIN")
        assert connection.connection.driver_connection.in_transaction
        with Operations.context(MigrationContext.configure(connection)):
            namespace["upgrade"]()
        result = connection.execute(text("SELECT e.content, e.published_revision_id, r.content, c.revision_id FROM knowledge_entries e JOIN knowledge_revisions r ON r.id=e.published_revision_id JOIN knowledge_chunks c ON c.source_entry_id=e.id")).one()
        assert tuple(result) == ("original", "legacy_47", "original", "legacy_47")
        assert connection.execute(text("SELECT count(*) FROM qa_cache_entries")).scalar_one() == 0
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        connection.rollback()  # This is an experiment, not a persisted repair.
    engine.dispose()
