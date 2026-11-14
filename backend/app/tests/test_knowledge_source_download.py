import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import create_admin_token
from app.api.knowledge import router
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.core.exceptions import register_exception_handlers
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, SourceDocument, SourceDocumentVersion
from app.tests.async_db import open_test_session


def test_admin_download_requires_current_revision_and_stays_within_upload_root(tmp_path):
    root = tmp_path / 'uploads'
    root.mkdir()
    (root / 'source.pdf').write_bytes(b'%PDF-synthetic')
    outside = tmp_path / 'outside.pdf'
    outside.write_bytes(b'private')
    settings = Settings(knowledge_upload_dir=str(root), admin_token_secret='test-download-secret')
    db_path = str(tmp_path / 'source.db')

    async def seed():
        engine, session = await open_test_session(db_path)
        try:
            session.add_all([
                SourceDocument(id='doc', name='synthetic'),
                SourceDocumentVersion(id='version', document_id='doc', sha256='a' * 64, storage_path='source.pdf', original_filename='synthetic.pdf', mime_type='application/pdf'),
            ])
            entry = KnowledgeEntry(title='资料', category='general', content='原文', source='synthetic.pdf')
            session.add(entry)
            await session.flush()
            revision = KnowledgeRevision(id='revision', knowledge_entry_id=entry.id, title='资料', category='general', content='原文', source='synthetic.pdf', source_document_version_id='version')
            session.add(revision)
            await session.flush()
            entry.draft_revision_id = revision.id
            await session.commit()
            return entry.id
        finally:
            await session.close()
            await engine.dispose()
    entry_id = asyncio.run(seed())
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix='/api/knowledge')
    app.dependency_overrides[get_app_settings] = lambda: settings

    async def database():
        engine, session = await open_test_session(db_path)
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()
    app.dependency_overrides[get_db_session] = database
    headers = {'Authorization': 'Bearer ' + create_admin_token(settings.admin_token_secret)}
    url = f'/api/knowledge/{entry_id}/source'
    with TestClient(app) as client:
        assert client.get(url, params={'revision_id': 'revision'}).status_code == 401
        assert client.get(url, params={'revision_id': 'old'}, headers=headers).status_code == 409
        response = client.get(url, params={'revision_id': 'revision'}, headers=headers)
        assert response.status_code == 200 and response.content == b'%PDF-synthetic'
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['content-disposition'].startswith('attachment;')

        async def change_path():
            engine, session = await open_test_session(db_path)
            try:
                version = await session.get(SourceDocumentVersion, 'version')
                version.storage_path = '../outside.pdf'
                await session.commit()
            finally:
                await session.close()
                await engine.dispose()
        asyncio.run(change_path())
        assert client.get(url, params={'revision_id': 'revision'}, headers=headers).status_code == 404
