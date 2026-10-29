import asyncio
import json
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import itinerary
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision
from app.tests.async_db import open_test_session


class ItineraryCatalogApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_endpoint_returns_only_public_current_attractions(self):
        engine, db = await open_test_session()
        app = FastAPI()
        app.include_router(itinerary.router, prefix="/api/itinerary")

        async def get_db():
            yield db

        app.dependency_overrides[get_db_session] = get_db
        app.dependency_overrides[get_app_settings] = lambda: Settings(
            site_id="lingshan", admin_token_secret="test-secret",
        )
        try:
            active = KnowledgeEntry(
                title="灵山大佛", category="景点信息", content="正式资料", source="official.pdf",
                aliases="大佛|灵山大佛", metadata_json=json.dumps({"attraction_id": "LS-011"}),
            )
            draft = KnowledgeEntry(
                title="待审核景点", category="景点信息", content="草稿", source="draft.pdf",
                aliases="", metadata_json=json.dumps({"attraction_id": "LS-012"}),
            )
            db.add_all([active, draft])
            await db.flush()
            revision = KnowledgeRevision(
                id=str(uuid4()), knowledge_entry_id=active.id, title=active.title,
                category=active.category, content=active.content, source=active.source,
                aliases=active.aliases, metadata_json=active.metadata_json,
            )
            withdrawn_revision = KnowledgeRevision(
                id=str(uuid4()), knowledge_entry_id=draft.id, title=draft.title,
                category=draft.category, content=draft.content, source=draft.source,
                aliases=draft.aliases, metadata_json=draft.metadata_json,
            )
            db.add_all([revision, withdrawn_revision])
            await db.flush()
            active.published_revision_id = revision.id
            draft.published_revision_id = withdrawn_revision.id
            draft.withdrawn_at = datetime.now(UTC)
            await db.commit()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                response = await client.get("/api/itinerary/catalog")

            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()
            self.assertEqual([item["spot_code"] for item in data["items"]], ["LS-011"])
            self.assertEqual(data["items"][0]["entry_id"], str(active.id))
            self.assertEqual(data["items"][0]["published_revision_id"], revision.id)
            self.assertIsNone(data["items"][0]["latitude"])
            self.assertTrue(data["digest"])
        finally:
            await db.close()
            await engine.dispose()
