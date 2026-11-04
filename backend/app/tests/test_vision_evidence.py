import asyncio
from types import SimpleNamespace

from app.schemas.chat import VisionConfirmation, VisionContext
from app.schemas.selection import SelectionContext
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.rag.base import RetrievalScope
from app.services.qa.vision_evidence import resolve_vision_evidence


class Catalog:
    async def list_for_site(self, site_id: str):
        return SimpleNamespace(entries=[SimpleNamespace(
            site_id="lingshan",
            spot_code="LS-01",
            published_revision_id="revision-1",
            entry_id="42",
            title="灵山梵宫",
        )])


def _resolved() -> ResolvedInteraction:
    return ResolvedInteraction(
        selection=SelectionContext(mode="attraction", attraction_id=9),
        scope=RetrievalScope(source_entry_id=9),
        resolution_source="selection",
        active_subject="历史选择",
    )


def test_confirmed_vision_uses_matching_published_catalog_entry_as_retrieval_scope():
    async def scenario():
        result = await resolve_vision_evidence(
            VisionContext(confirmation=VisionConfirmation(
                site_id="lingshan", spot_code="LS-01", published_revision_id="revision-1",
            )),
            _resolved(),
            vision_catalog=Catalog(),
            vision_site_id="lingshan",
        )

        assert result.error_code is None
        assert result.confirmed_title == "灵山梵宫"
        assert result.resolved.scope == RetrievalScope(source_entry_id=42)
        assert result.resolved.active_subject == "灵山梵宫"

    asyncio.run(scenario())


def test_unconfirmed_vision_does_not_reuse_previous_attraction_scope():
    async def scenario():
        result = await resolve_vision_evidence(
            VisionContext(candidate_attractions=["灵山梵宫"], retrieval_query="梵宫建筑"),
            _resolved(),
            vision_catalog=Catalog(),
            vision_site_id="lingshan",
        )

        assert result.error_code is None
        assert result.confirmed_title is None
        assert result.resolved.scope is None
        assert result.resolved.active_subject is None
        assert "vision_scope_unconfirmed" in result.resolved.warnings

    asyncio.run(scenario())


def test_stale_vision_confirmation_returns_explicit_error_without_fallback_scope():
    async def scenario():
        result = await resolve_vision_evidence(
            VisionContext(confirmation=VisionConfirmation(
                site_id="lingshan", spot_code="LS-01", published_revision_id="old-revision",
            )),
            _resolved(),
            vision_catalog=Catalog(),
            vision_site_id="lingshan",
        )

        assert result.error_code == "vision_confirmation_stale"
        assert result.resolved.scope is None

    asyncio.run(scenario())
