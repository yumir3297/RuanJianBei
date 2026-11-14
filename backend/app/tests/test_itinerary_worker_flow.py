"""Isolated API-to-worker-to-confirmation contract with a synthetic provider."""
import asyncio
import json
import os
import runpy
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


@pytest.mark.parametrize('separate_worker', [False, True])
def test_itinerary_proposal_is_persisted_only_after_confirmation(monkeypatch, tmp_path, separate_worker):
    async def scenario():
        import httpx
        from fastapi import FastAPI
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.api import tour_sessions
        from app.core.config import Settings
        from app.core.deps import get_app_settings, get_db_session
        from app.models.knowledge_workspace import KnowledgeState
        from app.repositories.tour_session import TourSessionRepository
        from app.schemas.itinerary import TourSnapshotV2
        from app.services.itinerary.intent import snapshot_digest
        from app.services.tool_execution import handlers
        from app.services.tool_execution.runner import ToolRunner
        from app.tests.async_db import open_test_session

        engine, initial = await open_test_session(str(tmp_path / 'flow.sqlite'))
        await initial.close()
        sessions = async_sessionmaker(bind=engine, expire_on_commit=False)
        # create_all does not run the migration that initializes this singleton.
        async with sessions() as db:
            db.add(KnowledgeState(id=1, epoch=1))
            await db.commit()
        settings = Settings(site_id='demo', admin_token_secret='isolated-test-secret',
                            llm_provider='openai', llm_api_key='synthetic',
                            llm_base_url='http://synthetic.invalid/v1', llm_model='synthetic')
        app = FastAPI()
        app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
        async def db_dependency():
            async with sessions() as db:
                yield db
        app.dependency_overrides[get_db_session] = db_dependency
        app.dependency_overrides[get_app_settings] = lambda: settings
        monkeypatch.setattr(handlers, 'AsyncSessionLocal', sessions)
        monkeypatch.setattr(handlers, 'get_settings', lambda: settings)
        original_client = httpx.AsyncClient
        def provider(request):
            body = json.loads(request.content)
            request_data = json.loads(body['messages'][-1]['content'])
            assert request_data['request'] == '演示：增加十分钟休息'
            result = {'result': 'operations', 'operations': [{'type': 'add_rest',
                      'name': '演示休息', 'duration_minutes': 10}]}
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(result)}}]})
        def model_client(*args, **kwargs):
            return original_client(*args, transport=httpx.MockTransport(provider), **kwargs)
        try:
            async with original_client(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
                bootstrap = (await client.get('/api/tour-sessions/bootstrap')).json()
                headers = {'Origin': 'http://testserver', 'X-CSRF-Token': bootstrap['csrf_token']}
                snapshot = TourSnapshotV2()
                async with sessions() as db:
                    created = await TourSessionRepository(db).create_session(
                        bootstrap['identity_id'], 'demo', '隔离演示', snapshot.model_dump(mode='json'), 'create')
                session_id = created['id']
                path = f'/api/tour-sessions/{session_id}'
                digest = snapshot_digest(snapshot)
                payload = {'expected_version': 1, 'progress_version': 0, 'draft_digest': digest,
                           'draft_snapshot': snapshot.model_dump(mode='json'), 'text': '演示：增加十分钟休息'}
                response = await client.post(path + '/proposals', json=payload,
                                             headers={**headers, 'Idempotency-Key': 'proposal'})
                assert response.status_code == 202, response.text
                proposal_id = response.json()['id']
                if separate_worker:
                    # Run the actual local-only synthetic provider on an ephemeral port.
                    monkeypatch.setenv('DEMO_SYNTHETIC_CONFIRM', '1')
                    backend_root = Path(__file__).resolve().parents[2]
                    handler = runpy.run_path(str(backend_root / 'scripts_local_demo_itinerary_provider.py'))['Handler']
                    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    env = {'PATH': os.environ.get('PATH', ''), 'PYTHONPATH': str(backend_root),
                           'DATABASE_URL': f'sqlite+aiosqlite:///{tmp_path / "flow.sqlite"}',
                           'SITE_ID': 'demo', 'LLM_PROVIDER': 'demo_synthetic', 'LLM_API_KEY': 'synthetic',
                           'LLM_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1',
                           'LLM_MODEL': 'synthetic', 'ADMIN_TOKEN_SECRET': 'isolated-test-secret'}
                    try:
                        process = await asyncio.create_subprocess_exec(
                            sys.executable, '-m', 'app.services.tool_execution.worker', '--once',
                            cwd=tmp_path, env=env, stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE)
                        try:
                            stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
                        except asyncio.TimeoutError:
                            process.kill()
                            await process.communicate()
                            raise
                        assert process.returncode == 0, (stdout, stderr)
                    finally:
                        server.shutdown()
                        server.server_close()
                        thread.join()
                else:
                    # Model HTTP alone is replaced; runner, handler and persistence are real.
                    with monkeypatch.context() as model_patch:
                        model_patch.setattr('app.services.itinerary.intent.httpx.AsyncClient', model_client)
                        assert await ToolRunner(sessions, handlers.build_registry()).run_one('isolated-worker')
                detail = await client.get(path + '/proposals/' + proposal_id)
                assert detail.status_code == 200, detail.text
                proposal = detail.json()
                assert proposal['status'] == 'ready', proposal
                assert proposal['validation'].get('synthetic_demo', False) is separate_worker
                assert proposal['diff'][0]['after']['name'] == '演示休息'
                before = (await client.get(path)).json()
                assert before['version'] == 1 and before['snapshot']['stops'] == []
                apply_payload = {'expected_version': 1, 'progress_version': 0, 'draft_digest': digest}
                apply_headers = {**headers, 'Idempotency-Key': 'apply'}
                first = await client.post(path + '/proposals/' + proposal_id + '/apply',
                                          json=apply_payload, headers=apply_headers)
                assert first.status_code == 200, first.text
                replay = await client.post(path + '/proposals/' + proposal_id + '/apply',
                                           json=apply_payload, headers=apply_headers)
                assert replay.status_code == 200 and replay.json() == first.json()
                after = (await client.get(path)).json()
                assert after['version'] == 2
                assert len(after['snapshot']['stops']) == 1
                assert after['snapshot']['stops'][0]['duration_minutes'] == 10
                assert after['snapshot']['stops'][0]['created_by'] == ('demo_synthetic' if separate_worker else 'ai')
                restored = (await client.get(path + '/proposals/' + proposal_id)).json()
                assert restored['status'] == 'applied'
                assert restored['validation'].get('synthetic_demo', False) is separate_worker
                revisions = (await client.get(path + '/revisions')).json()['items']
                by_version = {revision['version']: revision['id'] for revision in revisions}
                empty = await client.post(path + '/restore/' + by_version[1] + '?expected_version=2',
                                          headers={**headers, 'Idempotency-Key': 'restore-empty'})
                assert empty.status_code == 200, empty.text
                assert empty.json()['snapshot']['stops'] == []
                restored_plan = await client.post(path + '/restore/' + by_version[2] + '?expected_version=3',
                                                  headers={**headers, 'Idempotency-Key': 'restore-proposal'})
                assert restored_plan.status_code == 200, restored_plan.text
                restored_stop = restored_plan.json()['snapshot']['stops'][0]
                assert restored_stop['created_by'] == ('demo_synthetic' if separate_worker else 'ai')
                if separate_worker:
                    assert '本地模拟' in restored_stop['evidence'][0]['label']
        finally:
            await engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize(('environment', 'url'), [
    ('production', 'http://127.0.0.1:18765/v1'),
    ('development', 'https://127.0.0.1:18765/v1'),
    ('development', 'http://example.com/v1'),
    ('development', 'http://user:pass@127.0.0.1:18765/v1'),
])
def test_synthetic_provider_rejects_nonlocal_or_production(monkeypatch, environment, url):
    from app.core.config import Settings
    from app.services.tool_execution import handlers
    from app.services.tool_execution.registry import ToolStepError

    settings = Settings(app_env=environment, llm_provider='demo_synthetic', llm_base_url=url)
    monkeypatch.setattr(handlers, 'get_settings', lambda: settings)
    with pytest.raises(ToolStepError) as error:
        asyncio.run(handlers._generate_itinerary_proposal(None, None))
    assert error.value.code == 'provider_unavailable'
    assert error.value.external_outcome == 'not_started'
