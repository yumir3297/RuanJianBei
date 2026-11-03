from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision


@dataclass(frozen=True, order=True)
class PublishedAttraction:
    site_id: str
    spot_code: str
    entry_id: str
    published_revision_id: str
    title: str
    aliases: tuple[str, ...] = ()
    source_label: str = ""
    latitude: float | None = None
    longitude: float | None = None
    coordinate_evidence_id: str | None = None


@dataclass(frozen=True)
class CatalogSnapshot:
    site_id: str
    entries: tuple[PublishedAttraction, ...]
    digest: str


@dataclass(frozen=True)
class ResolvedSpot:
    attraction: PublishedAttraction


@dataclass(frozen=True)
class AmbiguousSpot:
    value: str
    candidates: tuple[PublishedAttraction, ...]


@dataclass(frozen=True)
class UnknownSpot:
    value: str


SpotParseResult = ResolvedSpot | AmbiguousSpot | UnknownSpot


class PublishedAttractionSource(Protocol):
    """The implementation must return only entries from the active published revision."""

    async def list_published_attractions(self, site_id: str) -> Sequence[PublishedAttraction]: ...


class CatalogIntegrityError(ValueError):
    pass


class CatalogSiteMismatch(ValueError):
    pass


def _normalize(value: str) -> str:
    return re.sub(r"[\s\-‐‑‒–—_]+", "", value).casefold()


def build_catalog_snapshot(site_id: str, entries: Sequence[PublishedAttraction]) -> CatalogSnapshot:
    if not site_id.strip():
        raise CatalogIntegrityError("景区标识不能为空")
    current = [entry for entry in entries if entry.site_id == site_id]
    key_by_code: set[str] = set()
    for entry in current:
        if not entry.spot_code.strip() or not entry.title.strip():
            raise CatalogIntegrityError("已发布景点缺少景点代码或标题")
        if not entry.entry_id.strip() or not entry.published_revision_id.strip():
            raise CatalogIntegrityError(f"已发布景点缺少内容或修订引用: {entry.spot_code}")
        key = (entry.site_id, entry.spot_code)
        if key in key_by_code:
            raise CatalogIntegrityError(f"景区内景点代码重复: {entry.spot_code}")
        key_by_code.add(key)
        if (entry.latitude is None) != (entry.longitude is None):
            raise CatalogIntegrityError(f"坐标不完整: {entry.spot_code}")
        if entry.latitude is not None and not entry.coordinate_evidence_id:
            raise CatalogIntegrityError(f"坐标缺少依据: {entry.spot_code}")
        if entry.latitude is not None and not (-90 <= entry.latitude <= 90 and -180 <= entry.longitude <= 180):
            raise CatalogIntegrityError(f"坐标超出有效范围: {entry.spot_code}")
    ordered = tuple(sorted(current, key=lambda entry: entry.spot_code))
    data = [{
        "site_id": item.site_id, "spot_code": item.spot_code, "entry_id": item.entry_id,
        "published_revision_id": item.published_revision_id, "title": item.title,
        "aliases": sorted(set(item.aliases)), "source_label": item.source_label,
        "latitude": item.latitude, "longitude": item.longitude,
        "coordinate_evidence_id": item.coordinate_evidence_id,
    } for item in ordered]
    digest = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return CatalogSnapshot(site_id, ordered, digest)


class PublishedAttractionCatalog:
    def __init__(self, source: PublishedAttractionSource) -> None:
        self.source = source

    async def list_for_site(self, site_id: str) -> CatalogSnapshot:
        rows = await self.source.list_published_attractions(site_id)
        return build_catalog_snapshot(site_id, rows)


class K01PublishedAttractionSource:
    """Read K01's current published revisions for this single-site application.

    K01 currently stores no per-entry site_id; the caller's configured site_id
    scopes this single-site database. A mismatched site is rejected rather than
    silently returning the same global catalog for another park.
    """

    def __init__(self, session: AsyncSession, *, site_id: str) -> None:
        self.session = session
        self.site_id = site_id

    async def list_published_attractions(self, site_id: str) -> Sequence[PublishedAttraction]:
        if site_id != self.site_id:
            raise CatalogSiteMismatch("景点目录仅绑定当前配置的景区")
        result = await self.session.execute(
            select(KnowledgeEntry, KnowledgeRevision)
            .join(KnowledgeRevision, KnowledgeRevision.id == KnowledgeEntry.published_revision_id)
            .where(
                KnowledgeEntry.category == "景点信息",
                KnowledgeEntry.published_revision_id.is_not(None),
                KnowledgeEntry.withdrawn_at.is_(None),
                KnowledgeRevision.knowledge_entry_id == KnowledgeEntry.id,
                KnowledgeRevision.category == "景点信息",
            )
            .order_by(KnowledgeEntry.id.asc())
            .execution_options(populate_existing=True)
        )
        entries: list[PublishedAttraction] = []
        for entry, revision in result.all():
            metadata = _parse_metadata(revision.metadata_json)
            spot_code = metadata.get("attraction_id")
            if not isinstance(spot_code, str) or not spot_code.strip():
                # A published attraction without a stable imported identity may
                # remain in the general knowledge base, but is not a route stop.
                continue
            latitude, longitude, coordinate_evidence_id = _published_coordinates(metadata)
            aliases = tuple(alias.strip() for alias in (revision.aliases or "").split("|") if alias.strip())
            entries.append(PublishedAttraction(
                site_id=site_id,
                spot_code=spot_code.strip(),
                entry_id=str(entry.id),
                published_revision_id=revision.id,
                title=revision.title,
                aliases=aliases,
                source_label=revision.source,
                latitude=latitude,
                longitude=longitude,
                coordinate_evidence_id=coordinate_evidence_id,
            ))
        return entries


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _published_coordinates(metadata: dict) -> tuple[float | None, float | None, str | None]:
    evidence_id = metadata.get("coordinate_evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        return None, None, None
    try:
        latitude = float(metadata["latitude"])
        longitude = float(metadata["longitude"])
    except (KeyError, TypeError, ValueError):
        return None, None, None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None, None, None
    return latitude, longitude, evidence_id.strip()


def parse_spot_reference(value: str, catalog: CatalogSnapshot) -> SpotParseResult:
    query = _normalize(value)
    if not query:
        return UnknownSpot(value)
    direct = [item for item in catalog.entries if _normalize(item.spot_code) == query]
    matches = direct or [
        item for item in catalog.entries
        if query in {_normalize(item.title), *(_normalize(alias) for alias in item.aliases)}
    ]
    unique = {item.spot_code: item for item in matches}
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) == 1:
        return ResolvedSpot(ordered[0])
    if ordered:
        return AmbiguousSpot(value, ordered)
    return UnknownSpot(value)
