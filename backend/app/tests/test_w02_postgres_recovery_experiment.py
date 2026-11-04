"""Opt-in destructive-schema experiment for a disposable PostgreSQL database only."""
import asyncio
import hashlib
import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not os.getenv('GUIDE_TEST_POSTGRES_URL') or not os.getenv('GUIDE_TEST_W02_REPO'), reason='requires disposable PostgreSQL and original W02 git repository')


def test_w02_postgres_knowledge_migration_rollback_and_retry():
    url = make_url(os.environ['GUIDE_TEST_POSTGRES_URL'])
    assert url.drivername == 'postgresql+asyncpg'
    assert (url.database or '').startswith('guide_test_')
    assert not url.host and url.query.get('host', '').startswith('/private/tmp/')
    source = subprocess.check_output(['git', 'show', 'codex/w02-preserved-snapshot:backend/alembic/versions/f1b4c9d76e20_add_tool_execution.py'], cwd=os.environ['GUIDE_TEST_W02_REPO'])
    assert hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest() == '9fa9e78f05c452c9a35238bec347017f3550d499'
    versions = ROOT / 'alembic' / 'versions'
    names = ['b667a1ecf225_initial_schema.py', 'a1c7f2d9b4e0_add_visitor_memories.py', 'd7c4a81e5f20_add_tour_sessions.py', 'e9f4c2b8016a_add_tour_session_events.py']
    def load(code, label):
        namespace = {}
        exec(compile(code, label, 'exec'), namespace)
        return namespace['upgrade']
    upgrades = [load((versions / name).read_text(), name) for name in names]
    upgrades.append(load(source, 'original-w02-f1'))
    knowledge_upgrade = load((versions / 'c84d0f1a7b92_add_knowledge_workspace.py').read_text(), 'knowledge-c84')
    schema = 'w02_exp_' + uuid4().hex

    async def scenario():
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            try:
                await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
                await conn.execute(text(f'SET search_path TO "{schema}"'))
                await conn.commit()
                def invoke(sync, funcs):
                    with Operations.context(MigrationContext.configure(sync)):
                        for fn in funcs: fn()
                await conn.run_sync(invoke, upgrades)
                await conn.execute(text("INSERT INTO knowledge_entries (id,title,category,content,source,aliases,created_at,updated_at) VALUES (47,'test','test','original','test','',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
                await conn.execute(text("INSERT INTO knowledge_chunks (chunk_id,source_entry_id,chunk_index,title,category,content,source,created_at) VALUES ('c47',47,0,'test','test','chunk','test',CURRENT_TIMESTAMP)"))
                await conn.execute(text("INSERT INTO qa_cache_entries (normalized_query,answer,sources,expires_at,created_at) VALUES ('q','a','[]','2099-01-01',CURRENT_TIMESTAMP)"))
                await conn.commit()
                await conn.run_sync(invoke, [knowledge_upgrade])
                await conn.rollback()
                assert (await conn.execute(text("SELECT to_regclass('knowledge_revisions')"))).scalar_one() is None
                assert (await conn.execute(text('SELECT content FROM knowledge_entries WHERE id=47'))).scalar_one() == 'original'
                assert (await conn.execute(text("SELECT content FROM knowledge_chunks WHERE chunk_id='c47'"))).scalar_one() == 'chunk'
                assert (await conn.execute(text('SELECT count(*) FROM qa_cache_entries'))).scalar_one() == 1
                await conn.commit()
                await conn.run_sync(invoke, [knowledge_upgrade])
                row = (await conn.execute(text("SELECT e.published_revision_id, c.revision_id FROM knowledge_entries e JOIN knowledge_chunks c ON c.source_entry_id=e.id WHERE e.id=47"))).one()
                assert tuple(row) == ('legacy_47', 'legacy_47')
                assert (await conn.execute(text('SELECT count(*) FROM qa_cache_entries'))).scalar_one() == 0
                await conn.rollback()
            finally:
                await conn.rollback()
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                await conn.commit()
        await engine.dispose()
    asyncio.run(scenario())
