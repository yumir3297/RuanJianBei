from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.repositories.route import RouteRepository
from app.schemas.selection import (
    AttractionOption,
    QuickSelectBootstrapResponse,
    QuickTopicRead,
    RouteOption,
)


router = APIRouter()


@router.get("/bootstrap", response_model=QuickSelectBootstrapResponse)
async def get_quick_select_bootstrap(
    session: Session = Depends(get_db_session),
) -> QuickSelectBootstrapResponse:
    topics = QuickTopicRepository(session).list_enabled()
    attractions = KnowledgeRepository(session).list_by_category("景点信息")
    routes = RouteRepository(session).list_all()

    return QuickSelectBootstrapResponse(
        topics=[
            QuickTopicRead(
                key=topic.key,
                label=topic.label,
                category=topic.category,
                icon=topic.icon,
                sort_order=topic.sort_order,
            )
            for topic in topics
        ],
        attractions=[_to_attraction_option(entry) for entry in attractions],
        routes=[
            RouteOption(
                id=route.id,
                title=route.title,
                duration_label=route.duration_label,
                tags=[tag for tag in route.tags.split("|") if tag],
            )
            for route in routes
        ],
    )


def _to_attraction_option(entry) -> AttractionOption:
    metadata = _parse_metadata(entry.metadata_json)
    return AttractionOption(
        id=entry.id,
        title=entry.title,
        scenic_area=_optional_string(metadata.get("scenic_area")),
        attraction_code=_optional_string(metadata.get("attraction_id")),
    )


def _parse_metadata(raw_metadata: str | None) -> dict:
    if not raw_metadata:
        return {}
    try:
        metadata = json.loads(raw_metadata)
    except (TypeError, ValueError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _optional_string(value) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
