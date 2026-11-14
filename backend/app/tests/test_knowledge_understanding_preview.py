import asyncio
import json

import httpx
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, SourceDocument, SourceDocumentVersion
from app.services.knowledge.understanding_preview import PreviewRequest, preview_understanding
from app.tests.async_db import open_test_session


def test_preview_validates_quote_and_never_writes_candidate(tmp_path):
    async def scenario():
        engine, session = await open_test_session(str(tmp_path / 'preview.db'))
        try:
            session.add(SourceDocument(id='doc', name='synthetic'))
            session.add(SourceDocumentVersion(id='version', document_id='doc', sha256='a' * 64, storage_path='synthetic', original_filename='synthetic.json', mime_type='application/json'))
            entry = KnowledgeEntry(title='景点', category='待分类', content='原文内容', source='synthetic.json')
            session.add(entry)
            await session.flush()
            session.add(KnowledgeRevision(id='draft', knowledge_entry_id=entry.id, title='景点', category='待分类', content='原文内容', source='synthetic.json', source_document_version_id='version', section_path='section', content_hash='hash'))
            entry.draft_revision_id = 'draft'
            await session.commit()
            request = PreviewRequest(expected_version=entry.lock_version, draft_revision_id='draft')
            settings = Settings(knowledge_understanding_enabled=True, llm_provider='stub')
            result = await preview_understanding(session, settings, entry.id, request)
            assert result['mode'] == 'synthetic_stub' and result['candidate']['quote'] == '原文内容'
            assert result['fact_checked'] is False and result['source_document_version_id'] == 'version'
            assert len((await session.scalars(select(KnowledgeRevision))).all()) == 1
            assert entry.published_revision_id is None

            async def bad_quote(_request):
                body = {'choices': [{'message': {'content': json.dumps({'content': '模型候选', 'quote': '不存在的原文'}, ensure_ascii=False)}}]}
                return httpx.Response(200, json=body)
            async with httpx.AsyncClient(transport=httpx.MockTransport(bad_quote)) as client:
                remote = Settings(knowledge_understanding_enabled=True, llm_provider='openai', llm_api_key='test-key', llm_base_url='https://example.invalid/v1', llm_model='test')
                with pytest.raises(AppError) as exc:
                    await preview_understanding(session, remote, entry.id, request, client=client)
                assert exc.value.error_code == 'understanding_unverified_quote'
            async def valid_quote(_request):
                body = {'choices': [{'message': {'content': json.dumps({'content': '候选，需要人工核对', 'quote': '原文'}, ensure_ascii=False)}}]}
                return httpx.Response(200, json=body)
            async with httpx.AsyncClient(transport=httpx.MockTransport(valid_quote)) as client:
                model_result = await preview_understanding(session, remote, entry.id, request, client=client)
                assert model_result['mode'] == 'model' and model_result['candidate']['quote'] == '原文'
                assert model_result['fact_checked'] is False
            async def changed_during_request(_request):
                from sqlalchemy import update
                other_engine, other_session = await open_test_session(str(tmp_path / 'preview.db'))
                try:
                    await other_session.execute(update(KnowledgeEntry).where(KnowledgeEntry.id == entry.id).values(lock_version=entry.lock_version + 1))
                    await other_session.commit()
                finally:
                    await other_session.close()
                    await other_engine.dispose()
                return await valid_quote(_request)
            async with httpx.AsyncClient(transport=httpx.MockTransport(changed_during_request)) as client:
                with pytest.raises(AppError) as changed:
                    await preview_understanding(session, remote, entry.id, request, client=client)
                assert changed.value.error_code == 'knowledge_version_conflict'
            with pytest.raises(AppError) as disabled:
                await preview_understanding(session, Settings(knowledge_understanding_enabled=False), entry.id, request)
            assert disabled.value.error_code == 'understanding_disabled'
            with pytest.raises(AppError) as stale:
                await preview_understanding(session, settings, entry.id, PreviewRequest(expected_version=entry.lock_version + 1, draft_revision_id='draft'))
            assert stale.value.error_code == 'knowledge_version_conflict'
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_preview_endpoint_requires_admin_token(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.auth import create_admin_token
    from app.api.knowledge import router
    from app.core.deps import get_app_settings, get_db_session
    from app.core.exceptions import register_exception_handlers

    app = FastAPI()
    app.include_router(router, prefix='/api/knowledge')
    register_exception_handlers(app)
    settings = Settings(knowledge_understanding_enabled=True, llm_provider='stub', admin_token_secret='test-understanding-secret')
    app.dependency_overrides[get_app_settings] = lambda: settings
    async def database():
        engine, session = await open_test_session(str(tmp_path / 'auth.db'))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()
    app.dependency_overrides[get_db_session] = database
    with TestClient(app) as client:
        body = {'expected_version': 1, 'draft_revision_id': 'draft'}
        assert client.post('/api/knowledge/1/understanding-preview', json=body).status_code == 401
        token = create_admin_token(settings.admin_token_secret)
        assert client.post('/api/knowledge/1/understanding-preview', json=body, headers={'Authorization': f'Bearer {token}'}).status_code == 404
