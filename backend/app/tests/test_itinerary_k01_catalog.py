import json
import unittest
from uuid import uuid4

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.services.itinerary.catalog import CatalogSiteMismatch, K01PublishedAttractionSource, PublishedAttractionCatalog
from app.tests.async_db import open_test_session


class K01PublishedCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine, self.db = await open_test_session()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()

    async def _entry(self, *, title, metadata, published=True, withdrawn=False, aliases=""):
        entry = KnowledgeEntry(
            title=title, category="景点信息", content=f"{title}正文", source="景区资料",
            aliases=aliases, metadata_json=json.dumps(metadata, ensure_ascii=False),
        )
        self.db.add(entry)
        await self.db.flush()
        if published:
            revision_id = str(uuid4())
            revision = KnowledgeRevision(
                id=revision_id, knowledge_entry_id=entry.id, title=entry.title,
                category=entry.category, content=entry.content, source=entry.source,
                aliases=entry.aliases, metadata_json=entry.metadata_json,
            )
            self.db.add(revision)
            await self.db.flush()
            entry.published_revision_id = revision_id
        if withdrawn:
            from datetime import UTC, datetime
            entry.withdrawn_at = datetime.now(UTC)
        await self.db.flush()
        return entry

    async def test_catalog_uses_only_current_published_nonwithdrawn_entries_with_codes(self):
        active = await self._entry(
            title="灵山大佛", metadata={"attraction_id": "LS-011", "scenic_area": "灵山胜境"},
            aliases="大佛|灵山大佛",
        )
        await self._entry(title="草稿景点", metadata={"attraction_id": "LS-012"}, published=False)
        await self._entry(title="已下架景点", metadata={"attraction_id": "LS-013"}, withdrawn=True)
        await self._entry(title="无稳定编号", metadata={"scenic_area": "灵山胜境"})

        catalog = await PublishedAttractionCatalog(
            K01PublishedAttractionSource(self.db, site_id="lingshan")
        ).list_for_site("lingshan")

        self.assertEqual([item.spot_code for item in catalog.entries], ["LS-011"])
        item = catalog.entries[0]
        self.assertEqual(item.entry_id, str(active.id))
        self.assertEqual(item.published_revision_id, active.published_revision_id)
        self.assertEqual(item.aliases, ("大佛", "灵山大佛"))

    async def test_catalog_rejects_a_site_other_than_the_configured_single_site(self):
        source = K01PublishedAttractionSource(self.db, site_id="lingshan")
        with self.assertRaises(CatalogSiteMismatch):
            await source.list_published_attractions("other-park")
