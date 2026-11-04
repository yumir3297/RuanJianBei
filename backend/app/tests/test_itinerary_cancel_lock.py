import asyncio
import json
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.repositories.tour_session import TourSessionRepository
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.tests.async_db import open_test_session


def test_cancelled_confirmation_releases_lock(tmp_path, monkeypatch):
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
        engine, seed = await open_test_session(str(tmp_path / 'api-race.db'))
        owner = TourIdentity(id='owner', credential_digest='a' * 64, expires_at=datetime.now(UTC) + timedelta(days=1))
        entry = KnowledgeEntry(title='景点', category='景点信息', content='资料', source='来源', aliases='', metadata_json=json.dumps({'attraction_id': 'A'}))
        seed.add_all([owner, entry, KnowledgeState(id=1, epoch=1)]); await seed.flush()
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
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                async with sessions() as writer:
                    await asyncio.wait_for(KnowledgeWorkspaceService(writer).withdraw(entry_id), timeout=3)
                async with sessions() as check:
                    assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 1
        finally:
            await engine.dispose()
    asyncio.run(run())

