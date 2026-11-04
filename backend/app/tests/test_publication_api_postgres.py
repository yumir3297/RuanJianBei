import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import os
import json
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import tour_sessions
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.tour_session import TourIdentity
from app.repositories.tour_session import TourSessionRepository
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
from app.services.knowledge.publication import KnowledgePublicationService
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.tests.test_knowledge_publication import FakeEmbedder, FakeVectorStore


@pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")
def test_postgres_publication_waits_for_real_proposal_confirmation(monkeypatch):
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")

    async def scenario():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        seed = sessions()
        assert await seed.get(KnowledgeState, 1) is not None
        metadata = json.dumps({"attraction_id": str(uuid4())})
        entry = KnowledgeEntry(title="测试景点", category="景点信息", content="资料", source="测试", metadata_json=metadata)
        seed.add(entry); await seed.flush()
        revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title, category=entry.category, content=entry.content, source=entry.source, metadata_json=metadata)
        seed.add(revision); await seed.flush(); entry.draft_revision_id = revision.id
        selected = [(entry.id, revision.id)]
        owner = TourIdentity(id=str(uuid4()), credential_digest=uuid4().hex * 2, expires_at=datetime.now(UTC) + timedelta(days=1))
        seed.add(owner); await seed.commit()
        snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60},
                    'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息', 'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
        repo = TourSessionRepository(seed)
        tour = await repo.create_session(owner.id, 'site', '行程', snapshot, 'create')
        catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
        generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': snapshot,
                     'diff': [], 'validation': {'status': 'pass', 'conflicts': []}, 'clarification': None}
        proposal = await repo.create_proposal(owner.id, tour['id'], 1, 0, 'a' * 64, catalog.digest, '调整', generated, 'proposal')
        await seed.close()
        publish_ready, publish_go, confirmation_locked, confirmation_go, update_started = (asyncio.Event() for _ in range(5))
        calls = 0
        original_catalog = PublishedAttractionCatalog.list_for_site
        async def catalog_gate(self, site_id):
            nonlocal calls
            result = await original_catalog(self, site_id)
            calls += 1
            if calls == 2:
                confirmation_locked.set()
                await asyncio.wait_for(confirmation_go.wait(), 3)
            return result
        monkeypatch.setattr(PublishedAttractionCatalog, 'list_for_site', catalog_gate)
        monkeypatch.setattr(tour_sessions, '_protect_write', lambda *_: None)
        app = FastAPI(); app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
        async def session_dep():
            async with sessions() as session:
                yield session
        app.dependency_overrides[get_db_session] = session_dep
        app.dependency_overrides[get_app_settings] = lambda: Settings(site_id='site')
        app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
        try:
            async with sessions() as publisher:
                service = KnowledgePublicationService(publisher, FakeEmbedder(), FakeVectorStore())
                job = await service.create_publication([{'entry_id': i, 'revision_id': r, 'expected_version': 1} for i, r in selected], idempotency_key=str(uuid4()))
                original_commit = service._commit_publication
                async def publish_gate(*args):
                    publish_ready.set()
                    await asyncio.wait_for(publish_go.wait(), 3)
                    return await original_commit(*args)
                monkeypatch.setattr(service, '_commit_publication', publish_gate)
                publication = asyncio.create_task(service.run_publication(job.id))
                request_task = None
                try:
                    await asyncio.wait_for(publish_ready.wait(), 3)
                    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                        request_task = asyncio.create_task(client.post(f"/api/tour-sessions/{tour['id']}/proposals/{proposal['id']}/apply", headers={'Idempotency-Key': 'apply'}, json={'expected_version': 1, 'progress_version': 0, 'draft_digest': 'a' * 64}))
                        await asyncio.wait_for(confirmation_locked.wait(), 3)
                        publish_go.set()
                        blocked = False
                        for _ in range(300):
                            if publication.done():
                                raise AssertionError("publication finished before confirmation committed")
                            async with sessions() as observer:
                                count = await observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%knowledge_state%'"))
                            if count:
                                blocked = True
                                break
                            await asyncio.sleep(.01)
                        assert blocked, "publication did not reach state lock wait"
                        confirmation_go.set()
                        response = await asyncio.wait_for(request_task, 3)
                        assert response.status_code == 200, response.text
                        await asyncio.wait_for(publication, 3)
                        assert (await service.get_publication(job.id)).state == 'succeeded'
                        async with sessions() as check:
                            assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 2
                            updated_catalog = await original_catalog(PublishedAttractionCatalog(K01PublishedAttractionSource(check, site_id='site')), 'site')
                            assert updated_catalog.digest != catalog.digest
                finally:
                    publish_go.set(); confirmation_go.set()
                    for task in (request_task, publication):
                        if task is not None and not task.done(): task.cancel()
                    await asyncio.gather(*(task for task in (request_task, publication) if task is not None), return_exceptions=True)
        finally:
            await engine.dispose()
    asyncio.run(scenario())


@pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")
def test_postgres_publication_first_rejects_old_proposal(monkeypatch):
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")

    async def scenario():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as seed:
                assert await seed.get(KnowledgeState, 1) is not None
                metadata = json.dumps({"attraction_id": str(uuid4())})
                entry = KnowledgeEntry(title="测试景点", category="景点信息", content="资料", source="测试", metadata_json=metadata)
                owner = TourIdentity(id=str(uuid4()), credential_digest=uuid4().hex * 2, expires_at=datetime.now(UTC) + timedelta(days=1))
                seed.add_all([entry, owner]); await seed.flush()
                revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title, category=entry.category, content=entry.content, source=entry.source, metadata_json=metadata)
                seed.add(revision); await seed.flush(); entry.draft_revision_id = revision.id
                await seed.commit()
                snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60}, 'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息', 'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
                repo = TourSessionRepository(seed)
                tour = await repo.create_session(owner.id, 'site', '行程', snapshot, 'create')
                catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
                generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': snapshot, 'diff': [], 'validation': {'status': 'pass', 'conflicts': []}, 'clarification': None}
                proposal = await repo.create_proposal(owner.id, tour['id'], 1, 0, 'a' * 64, catalog.digest, '调整', generated, 'proposal')
                entry_id, revision_id = entry.id, revision.id
            async with sessions() as publisher:
                service = KnowledgePublicationService(publisher, FakeEmbedder(), FakeVectorStore())
                job = await service.create_publication([{'entry_id': entry_id, 'revision_id': revision_id, 'expected_version': 1}], idempotency_key=str(uuid4()))
                await service.run_publication(job.id)
                assert (await service.get_publication(job.id)).state == 'succeeded'
            app = FastAPI(); app.include_router(tour_sessions.router, prefix='/api/tour-sessions')
            async def session_dep():
                async with sessions() as session:
                    yield session
            app.dependency_overrides[get_db_session] = session_dep
            app.dependency_overrides[get_app_settings] = lambda: Settings(site_id='site')
            app.dependency_overrides[tour_sessions.get_tour_identity] = lambda: owner
            monkeypatch.setattr(tour_sessions, '_protect_write', lambda *_: None)
            async with sessions() as check:
                new_catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(check, site_id='site')).list_for_site('site')
                assert new_catalog.digest != catalog.digest
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                response = await client.post(f"/api/tour-sessions/{tour['id']}/proposals/{proposal['id']}/apply", headers={'Idempotency-Key': 'apply'}, json={'expected_version': 1, 'progress_version': 0, 'draft_digest': 'a' * 64})
                assert response.status_code == 409, response.text
            async with sessions() as check:
                assert len(await TourSessionRepository(check).list_revisions(owner.id, tour['id'])) == 1
        finally:
            await engine.dispose()
    asyncio.run(scenario())
