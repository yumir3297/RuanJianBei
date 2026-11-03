"""Opt-in integration tests; dedicated disposable PostgreSQL only."""
import asyncio
import json
import os
from uuid import uuid4
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.repositories.tour_session import TourSessionRepository
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
from app.services.knowledge.workspace import KnowledgeWorkspaceService

pytestmark = pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")

def _safe_url():
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")
    return url

def test_postgres_api_rejects_catalog_withdrawn_after_initial_check(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api import tour_sessions
    from app.core.config import Settings
    from app.core.deps import get_app_settings, get_db_session
    from app.models.tour_session import TourIdentity

    async def run():
        engine = create_async_engine(_safe_url())
        seed = async_sessionmaker(engine, expire_on_commit=False)()
        owner = TourIdentity(id=str(uuid4()), credential_digest=uuid4().hex * 2, expires_at=datetime.now(UTC) + timedelta(days=1))
        entry = KnowledgeEntry(title='景点', category='景点信息', content='资料', source='来源', aliases='', metadata_json=json.dumps({'attraction_id': 'A'}))
        seed.add_all([owner, entry]); await seed.flush()
        rev = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title, category=entry.category, content=entry.content, source=entry.source, aliases='', metadata_json=entry.metadata_json)
        seed.add(rev); await seed.flush(); entry.published_revision_id = rev.id
        await seed.commit(); entry_id = entry.id
        snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60}, 'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息', 'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
        repo = TourSessionRepository(seed)
        tour = await repo.create_session(owner.id, 'site', '行程', snapshot, 'create')
        catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
        candidate = json.loads(json.dumps(snapshot)); candidate['stops'].append({'stop_id': str(uuid4()), 'kind': 'visit', 'spot_code': 'A', 'name': '景点', 'duration_minutes': 10, 'duration_basis': 'estimate'})
        generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': candidate, 'diff': [], 'validation': {'status': 'unverified', 'conflicts': []}, 'clarification': None}
        proposal = await repo.create_proposal(owner.id, tour['id'], 1, 0, 'a'*64, catalog.digest, '添加景点', generated, 'proposal')
        await seed.close()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        original = TourSessionRepository.apply_proposal
        async def after_check(self, *args, **kwargs):
            async with sessions() as writer:
                await asyncio.wait_for(KnowledgeWorkspaceService(writer).withdraw(entry_id), timeout=2)
            return await original(self, *args, **kwargs)
        monkeypatch.setattr(TourSessionRepository, 'apply_proposal', after_check)
        monkeypatch.setattr(tour_sessions, '_protect_write', lambda *_: None)
        app = FastAPI(); app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
        async def session_dep():
            async with sessions() as session:
                yield session
        app.dependency_overrides[get_db_session] = session_dep
        app.dependency_overrides[get_app_settings] = lambda: Settings(site_id='site')
        app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                response = await client.post(f"/api/tour-sessions/{tour['id']}/proposals/{proposal['id']}/apply", headers={'Idempotency-Key': 'apply'}, json={'expected_version': 1, 'progress_version': 0, 'draft_digest': 'a'*64})
                assert response.status_code == 409, response.text
            async with sessions() as check:
                assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 1
        finally:
            await engine.dispose()
    asyncio.run(run())


def test_postgres_api_confirmation_locks_catalog_until_commit(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api import tour_sessions
    from app.core.config import Settings
    from app.core.deps import get_app_settings, get_db_session
    from app.models.tour_session import TourIdentity
    from app.models.knowledge_workspace import KnowledgeState
    from sqlalchemy import event

    async def run():
        engine = create_async_engine(_safe_url())
        seed = async_sessionmaker(engine, expire_on_commit=False)()
        owner = TourIdentity(id=str(uuid4()), credential_digest=uuid4().hex * 2, expires_at=datetime.now(UTC) + timedelta(days=1))
        entry = KnowledgeEntry(title='景点', category='景点信息', content='资料', source='来源', aliases='', metadata_json=json.dumps({'attraction_id': 'A'}))
        seed.add_all([owner, entry]); await seed.flush()
        rev = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title, category=entry.category, content=entry.content, source=entry.source, aliases='', metadata_json=entry.metadata_json)
        seed.add(rev); await seed.flush(); entry.published_revision_id = rev.id
        await seed.commit(); entry_id = entry.id
        snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60}, 'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息', 'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
        repo = TourSessionRepository(seed)
        tour = await repo.create_session(owner.id, 'site', '行程', snapshot, 'create')
        catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
        candidate = json.loads(json.dumps(snapshot)); candidate['stops'].append({'stop_id': str(uuid4()), 'kind': 'visit', 'spot_code': 'A', 'name': '景点', 'duration_minutes': 10, 'duration_basis': 'estimate'})
        generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': candidate, 'diff': [], 'validation': {'status': 'unverified', 'conflicts': []}, 'clarification': None}
        proposal = await repo.create_proposal(owner.id, tour['id'], 1, 0, 'a'*64, catalog.digest, '添加景点', generated, 'proposal')
        await seed.close()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        locked_read = asyncio.Event()
        release = asyncio.Event()
        writer_started = asyncio.Event()
        calls = 0
        original_catalog = PublishedAttractionCatalog.list_for_site
        async def pause_after_locked_read(self, site_id):
            nonlocal calls
            result = await original_catalog(self, site_id)
            calls += 1
            if calls == 2:  # API first read followed by repository locked read
                locked_read.set()
                await asyncio.wait_for(release.wait(), timeout=3)
            return result
        monkeypatch.setattr(PublishedAttractionCatalog, 'list_for_site', pause_after_locked_read)
        @event.listens_for(engine.sync_engine, 'before_cursor_execute')
        def observe(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith('UPDATE KNOWLEDGE_ENTRIES'):
                writer_started.set()
        monkeypatch.setattr(tour_sessions, '_protect_write', lambda *_: None)
        app = FastAPI(); app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
        async def session_dep():
            async with sessions() as session:
                yield session
        app.dependency_overrides[get_db_session] = session_dep
        app.dependency_overrides[get_app_settings] = lambda: Settings(site_id='site')
        app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                task = asyncio.create_task(client.post(f"/api/tour-sessions/{tour['id']}/proposals/{proposal['id']}/apply", headers={'Idempotency-Key': 'apply'}, json={'expected_version': 1, 'progress_version': 0, 'draft_digest': 'a'*64}))
                await asyncio.wait_for(locked_read.wait(), timeout=3)
                async with sessions() as writer:
                    withdrawal = asyncio.create_task(KnowledgeWorkspaceService(writer).withdraw(entry_id))
                    try:
                        await asyncio.wait_for(writer_started.wait(), timeout=3)
                        with pytest.raises(TimeoutError):
                            await asyncio.wait_for(asyncio.shield(withdrawal), timeout=.1)
                        release.set()
                        response = await asyncio.wait_for(task, timeout=3)
                        assert response.status_code == 200, response.text
                        await asyncio.wait_for(withdrawal, timeout=3)
                    finally:
                        release.set()
                        if not withdrawal.done():
                            withdrawal.cancel()
                            await asyncio.gather(withdrawal, return_exceptions=True)
                async with sessions() as check:
                    assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 2
                    current_catalog = await original_catalog(PublishedAttractionCatalog(K01PublishedAttractionSource(check, site_id='site')), 'site')
                    assert current_catalog.entries == ()
        finally:
            await engine.dispose()
    asyncio.run(run())




def test_postgres_concurrent_identical_proposal_apply_replays_once(monkeypatch):
    from datetime import UTC, datetime, timedelta
    from app.models.tour_session import TourIdentity
    from app.models.knowledge_workspace import KnowledgeState

    async def run():
        engine = create_async_engine(_safe_url())
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = str(uuid4())
        try:
            async with sessions() as seed:
                assert await seed.get(KnowledgeState, 1) is not None
                seed.add(TourIdentity(id=owner_id, credential_digest=uuid4().hex * 2,
                                      expires_at=datetime.now(UTC) + timedelta(days=1)))
                await seed.commit()
                snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60},
                            'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息',
                                       'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
                repo = TourSessionRepository(seed)
                tour = await repo.create_session(owner_id, 'site', '行程', snapshot, 'create')
                catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
                generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': snapshot,
                             'diff': [], 'validation': {'status': 'pass', 'conflicts': []}, 'clarification': None}
                proposal = await repo.create_proposal(owner_id, tour['id'], 1, 0, 'a' * 64,
                                                      catalog.digest, '调整', generated, 'proposal')
            original = TourSessionRepository._replay
            both = asyncio.Event()
            count = 0
            async def barrier(self, *args, **kwargs):
                nonlocal count
                result = await original(self, *args, **kwargs)
                if args[1] == 'proposal_apply' and result is None and count < 2:
                    count += 1
                    if count == 2: both.set()
                    await asyncio.wait_for(both.wait(), 5)
                return result
            monkeypatch.setattr(TourSessionRepository, '_replay', barrier)
            async def apply():
                async with sessions() as session:
                    return await TourSessionRepository(session).apply_proposal(
                        owner_id, tour['id'], proposal['id'], 1, 0, 'a' * 64, 'apply', catalog_site_id='site')
            first, second = await asyncio.wait_for(asyncio.gather(apply(), apply()), 10)
            assert first == second
            async with sessions() as check:
                assert len(await TourSessionRepository(check).list_revisions(owner_id, tour['id'])) == 2
        finally:
            await engine.dispose()
    asyncio.run(run())


def test_postgres_api_lock_timeout_retries_same_key(monkeypatch):
    from datetime import UTC, datetime, timedelta
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text, update
    from app.api import tour_sessions
    from app.core.config import Settings
    from app.core.deps import get_app_settings, get_db_session
    from app.models.knowledge_workspace import KnowledgeState
    from app.models.tour_session import TourIdentity

    async def run():
        engine = create_async_engine(_safe_url())
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner = TourIdentity(id=str(uuid4()), credential_digest=uuid4().hex * 2,
                             expires_at=datetime.now(UTC) + timedelta(days=1))
        try:
            async with sessions() as seed:
                assert await seed.get(KnowledgeState, 1) is not None
                seed.add(owner); await seed.commit()
                snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60},
                            'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息',
                                       'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
                repo = TourSessionRepository(seed)
                tour = await repo.create_session(owner.id, 'site', '行程', snapshot, 'create')
                catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
                generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': snapshot,
                             'diff': [], 'validation': {'status': 'pass', 'conflicts': []}, 'clarification': None}
                proposal = await repo.create_proposal(owner.id, tour['id'], 1, 0, 'a' * 64, catalog.digest,
                                                      '调整', generated, 'proposal')
            app = FastAPI(); app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
            async def session_dep():
                async with sessions() as session:
                    await session.execute(text("SET LOCAL lock_timeout = '100ms'"))
                    yield session
            app.dependency_overrides[get_db_session] = session_dep
            app.dependency_overrides[get_app_settings] = lambda: Settings(site_id='site')
            app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
            monkeypatch.setattr(tour_sessions, '_protect_write', lambda *_: None)
            path = f"/api/tour-sessions/{tour['id']}/proposals/{proposal['id']}/apply"
            payload = {'expected_version': 1, 'progress_version': 0, 'draft_digest': 'a' * 64}
            async with sessions() as holder:
                await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch))
                async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url='http://test') as client:
                    failed = await client.post(path, headers={'Idempotency-Key': 'apply'}, json=payload)
                    assert failed.status_code == 503, failed.text
                    async with sessions() as check:
                        assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 1
                    await holder.rollback()
                    result = await client.post(path, headers={'Idempotency-Key': 'apply'}, json=payload)
                    assert result.status_code == 200, result.text
                    assert result.json()['version'] == 2
        finally:
            await engine.dispose()
    asyncio.run(run())
