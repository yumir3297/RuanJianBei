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


@pytest.mark.xfail(strict=True, reason="catalog can change after the confirmation check")
def test_old_catalog_snapshot_is_rejected_after_real_withdrawal(tmp_path):
    async def run():
        engine, seed = await open_test_session(str(tmp_path / 'race.db'))
        entry = KnowledgeEntry(title='景点', category='景点信息', content='资料', source='来源', aliases='', metadata_json=json.dumps({'attraction_id': 'A'}))
        seed.add(entry); await seed.flush()
        revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title, category=entry.category, content=entry.content, source=entry.source, aliases='', metadata_json=entry.metadata_json)
        seed.add(revision); await seed.flush(); entry.published_revision_id = revision.id
        await seed.commit(); entry_id = entry.id
        snapshot = {'schema_version': 2, 'constraints': {'available_minutes': 60}, 'stops': [{'stop_id': str(uuid4()), 'kind': 'rest', 'name': '休息', 'duration_minutes': 10, 'duration_basis': 'user'}], 'legs': []}
        repo = TourSessionRepository(seed)
        tour = await repo.create_session('owner', 'site', '行程', snapshot, 'create')
        catalog = await PublishedAttractionCatalog(K01PublishedAttractionSource(seed, site_id='site')).list_for_site('site')
        candidate = json.loads(json.dumps(snapshot)); candidate['stops'].append({'stop_id': str(uuid4()), 'kind': 'visit', 'spot_code': 'A', 'name': '景点', 'duration_minutes': 10, 'duration_basis': 'estimate'})
        generated = {'status': 'ready', 'base_snapshot': snapshot, 'operations': [], 'candidate': candidate, 'diff': [], 'validation': {'status': 'unverified', 'conflicts': []}, 'clarification': None}
        proposal = await repo.create_proposal('owner', tour['id'], 1, 0, 'a'*64, catalog.digest, '添加景点', generated, 'proposal')
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as writer:
            await KnowledgeWorkspaceService(writer).withdraw(entry_id)
        try:
            with pytest.raises(ValueError):
                await repo.apply_proposal('owner', tour['id'], proposal['id'], 1, 0, 'a'*64, 'apply', catalog_entries={e.spot_code: e for e in catalog.entries})
        finally:
            await seed.close(); await engine.dispose()
    asyncio.run(run())
