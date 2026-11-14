from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.repositories.tour_session import TourSessionRepository
from app.schemas.itinerary import TourSnapshotV2
from app.services.itinerary.catalog import K01PublishedAttractionSource, PublishedAttractionCatalog
from app.services.itinerary.intent import ItineraryIntentService, IntentUnavailable, snapshot_digest
from app.services.tool_execution.registry import ToolContext, ToolHandler, ToolRegistry, ToolStepError


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ItineraryProposalInput(_StrictModel):
    proposal_id: str = Field(min_length=1, max_length=36)
    idempotency_key: str = Field(min_length=1, max_length=128)
    request_text: str = Field(min_length=2, max_length=1000)
    draft_digest: str = Field(min_length=64, max_length=64)
    normalized_draft_digest: str = Field(min_length=64, max_length=64)
    catalog_digest: str = Field(min_length=64, max_length=64)
    draft_snapshot: dict[str, Any]


class ItineraryProposalOutput(_StrictModel):
    status: Literal["ready", "needs_clarification"]
    clarification: str | None = Field(default=None, max_length=300)
    operations: list[dict[str, Any]] = Field(max_length=20)
    candidate: dict[str, Any]
    diff: list[dict[str, Any]] = Field(max_length=100)
    validation: dict[str, Any]


async def _generate_itinerary_proposal(
    payload: ItineraryProposalInput, context: ToolContext,
) -> ItineraryProposalOutput:
    settings = get_settings()
    synthetic = settings.llm_provider == "demo_synthetic"
    if synthetic:
        url = urlsplit(settings.llm_base_url)
        if (settings.app_env.strip().lower() not in {"development", "test"}
                or url.scheme != "http" or url.hostname != "127.0.0.1"
                or url.username is not None or url.password is not None):
            raise ToolStepError("provider_unavailable", external_outcome="not_started")
    if settings.llm_provider == "stub" or not all((
        settings.llm_api_key.strip(), settings.llm_base_url.strip(), settings.llm_model.strip(),
    )):
        raise ToolStepError("provider_unavailable", external_outcome="not_started")
    try:
        snapshot = TourSnapshotV2.model_validate(payload.draft_snapshot)
    except Exception as error:
        raise ToolStepError("invalid_persisted_input") from error
    if snapshot_digest(snapshot) != payload.normalized_draft_digest:
        raise ToolStepError("normalized_draft_digest_mismatch")

    async with AsyncSessionLocal() as session:
        catalog = await PublishedAttractionCatalog(
            K01PublishedAttractionSource(session, site_id=context.lease.site_id)
        ).list_for_site(context.lease.site_id)
    if catalog.digest != payload.catalog_digest:
        raise ToolStepError("catalog_changed", external_outcome="confirmed_failure")

    await context.mark_external_call()
    try:
        generated = await ItineraryIntentService().propose(
            payload.request_text, snapshot, catalog, settings,
        )
        if synthetic:
            generated["validation"]["synthetic_demo"] = True
    except IntentUnavailable as error:
        raise ToolStepError("provider_unavailable", external_outcome="unknown") from error
    except Exception as error:
        raise ToolStepError("proposal_generation_failed", external_outcome="unknown") from error
    return ItineraryProposalOutput.model_validate(generated)


async def _persist_itinerary_proposal(
    session: AsyncSession, lease: Any, output: ItineraryProposalOutput,
) -> None:
    payload = ItineraryProposalInput.model_validate(lease.input_payload)
    await TourSessionRepository(session).complete_reserved_proposal(
        lease.principal_id, lease.target_id, payload.proposal_id,
        output.model_dump(mode="json"), payload.idempotency_key, commit=False,
    )


def build_registry() -> ToolRegistry:
    """Return only production handlers explicitly approved and implemented in this repository."""
    registry = ToolRegistry()
    registry.register(ToolHandler(
        name="itinerary.proposal",
        version="1",
        workflow_schema_version="1",
        input_model=ItineraryProposalInput,
        output_model=ItineraryProposalOutput,
        execute=_generate_itinerary_proposal,
        persist_result=_persist_itinerary_proposal,
        retry_safe=False,
        max_attempts=1,
        timeout_seconds=60,
        recovery_mode="manual_retry",
    ))
    return registry
