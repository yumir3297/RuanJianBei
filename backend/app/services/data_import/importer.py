from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.behavior_summary import BehaviorSummary
from app.models.faq import FAQEntryRecord
from app.models.knowledge import KnowledgeEntry
from app.models.route import RouteTemplate
from app.repositories.behavior_summary import BehaviorSummaryRepository
from app.repositories.faq import FAQRepository
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_blind_spot import KnowledgeBlindSpotRepository
from app.repositories.qa_cache import QACacheRepository
from app.repositories.route import RouteRepository
from app.services.data_import.chunker import KnowledgeChunker


GENERIC_GUIDE_TITLES = {"讲解重点", "特色体验"}
SECTION_TYPE_BY_CATEGORY = {
    "历史文化": "overview",
    "实用贴士": "travel_tip",
    "游览路线": "route_overview",
    "景点解读": "feature_overview",
}


@dataclass(slots=True)
class DataImportReport:
    knowledge_imported: int
    chunk_imported: int
    faq_imported: int
    route_imported: int
    behavior_imported: int
    duration_ms: int


class ProcessedDataImporter:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.knowledge_repository = KnowledgeRepository(session)
        self.knowledge_chunk_repository = KnowledgeChunkRepository(session)
        self.faq_repository = FAQRepository(session)
        self.route_repository = RouteRepository(session)
        self.behavior_summary_repository = BehaviorSummaryRepository(session)
        self.qa_cache_repository = QACacheRepository(session)

    async def sync(self) -> DataImportReport:
        start = perf_counter()
        knowledge_payload = self._read_json(self.settings.knowledge_entries_file)
        guide_sections_payload = self._read_json(self.settings.guide_sections_file)
        faq_payload = self._read_json(self.settings.faq_file)
        route_payload = self._read_json(self.settings.route_recommendations_file)
        behavior_summary_payload = self._read_json(self.settings.visitor_behavior_summary_file)

        prepared_knowledge = self._prepare_knowledge_entries(
            knowledge_payload=knowledge_payload,
            guide_sections_payload=guide_sections_payload,
            route_payload=route_payload,
        )
        knowledge_count = await self._sync_knowledge_entries(prepared_knowledge)
        chunk_count = await self._sync_knowledge_chunks()
        faq_count = await self._sync_faq_entries(faq_payload)
        route_count = await self._sync_route_templates(route_payload)
        behavior_count = await self._sync_behavior_summary(behavior_summary_payload)

        await self.session.commit()
        await self.qa_cache_repository.invalidate()

        return DataImportReport(
            knowledge_imported=knowledge_count,
            chunk_imported=chunk_count,
            faq_imported=faq_count,
            route_imported=route_count,
            behavior_imported=behavior_count,
            duration_ms=int((perf_counter() - start) * 1000),
        )

    def _prepare_knowledge_entries(
        self,
        *,
        knowledge_payload: list[dict],
        guide_sections_payload: list[dict],
        route_payload: list[dict],
    ) -> list[dict]:
        guide_sections_map = {
            item["title"]: item["content"]
            for item in guide_sections_payload
            if item.get("title") and item.get("title") not in GENERIC_GUIDE_TITLES and item.get("content")
        }
        scenic_area = self._resolve_scenic_area(knowledge_payload)
        guide_document_name = self._resolve_guide_document_name(knowledge_payload, route_payload)

        prepared: list[dict] = []
        seen_keys: set[tuple[str, str]] = set()

        for item in knowledge_payload:
            title = str(item["title"]).strip()
            source = str(item["source"]).strip()
            metadata = dict(item.get("metadata") or {})
            category = str(item.get("category", "general")).strip()
            if title in guide_sections_map or category in SECTION_TYPE_BY_CATEGORY:
                if scenic_area:
                    metadata.setdefault("scenic_area", scenic_area)
                section_type = SECTION_TYPE_BY_CATEGORY.get(category)
                if section_type:
                    metadata["section_type"] = section_type

            prepared.append(
                {
                    "title": title,
                    "category": category,
                    "content": str(item.get("content", "")).strip(),
                    "source": source,
                    "aliases": list(item.get("aliases", [])),
                    "metadata_json": json.dumps(metadata, ensure_ascii=False) if metadata else None,
                }
            )
            seen_keys.add((title, source))

        for title, content in guide_sections_map.items():
            source = f"{guide_document_name} - {title}" if guide_document_name else title
            key = (title, source)
            if key in seen_keys:
                continue
            metadata = {}
            if scenic_area:
                metadata["scenic_area"] = scenic_area
            category = self._infer_guide_category(title)
            section_type = SECTION_TYPE_BY_CATEGORY.get(category)
            if section_type:
                metadata["section_type"] = section_type
            prepared.append(
                {
                    "title": title,
                    "category": category,
                    "content": str(content).strip(),
                    "source": source,
                    "aliases": [title, f"{scenic_area}{title}" if scenic_area else title],
                    "metadata_json": json.dumps(metadata, ensure_ascii=False) if metadata else None,
                }
            )
            seen_keys.add(key)

        return prepared

    async def _sync_knowledge_entries(self, entries: list[dict]) -> int:
        managed_sources = sorted({entry["source"] for entry in entries})
        existing_entries = {
            (entry.title, entry.source): entry
            for entry in await self.knowledge_repository.list_by_sources(
                managed_sources + [self.settings.default_knowledge_source]
            )
        }
        incoming_keys = {(entry["title"], entry["source"]) for entry in entries}

        for payload in entries:
            key = (payload["title"], payload["source"])
            entry = existing_entries.get(key)
            aliases = "|".join(payload["aliases"])
            if entry is None:
                self.session.add(
                    KnowledgeEntry(
                        title=payload["title"],
                        category=payload["category"],
                        content=payload["content"],
                        source=payload["source"],
                        aliases=aliases,
                        metadata_json=payload["metadata_json"],
                    )
                )
                continue

            entry.category = payload["category"]
            entry.content = payload["content"]
            entry.aliases = aliases
            entry.metadata_json = payload["metadata_json"]
            self.session.add(entry)

        for key, entry in existing_entries.items():
            if entry.source == self.settings.default_knowledge_source or key not in incoming_keys:
                await self.session.delete(entry)

        await self.session.flush()
        return len(entries)

    async def _sync_knowledge_chunks(self) -> int:
        entries = await self.knowledge_repository.list_all()
        chunks = KnowledgeChunker().build_chunks(entries)
        return await self.knowledge_chunk_repository.replace_all(chunks)

    async def _sync_faq_entries(self, payload: list[dict]) -> int:
        entries = [
            FAQEntryRecord(
                id=str(item["id"]).strip(),
                category=str(item.get("category", "general")).strip(),
                aliases_json=json.dumps(item.get("aliases", []), ensure_ascii=False),
                answer=str(item.get("answer", "")).strip(),
                sources_json=json.dumps(item.get("sources", []), ensure_ascii=False),
            )
            for item in payload
        ]
        blind_spot_repo = KnowledgeBlindSpotRepository(self.session)
        protected_faq_ids = await blind_spot_repo.list_resolved_faq_ids()
        return await self.faq_repository.replace_all(entries, preserve_ids=protected_faq_ids)

    async def _sync_route_templates(self, payload: list[dict]) -> int:
        entries = [
            RouteTemplate(
                id=str(item["id"]).strip(),
                title=str(item.get("title", "")).strip(),
                duration_label=str(item.get("duration_label", "")).strip(),
                route_plan=str(item.get("route_plan", "")).strip(),
                guide_points_json=json.dumps(item.get("guide_points", []), ensure_ascii=False),
                experiences_json=json.dumps(item.get("experiences", []), ensure_ascii=False),
                source=str(item.get("source", "")).strip(),
                tags="|".join(self._infer_route_tags(item)),
            )
            for item in payload
        ]
        return await self.route_repository.replace_all(entries)

    async def _sync_behavior_summary(self, payload: dict) -> int:
        summaries = [
            BehaviorSummary(
                dataset_name=str(payload.get("dataset_name", "")).strip(),
                intended_usage=str(payload.get("intended_usage", "")).strip(),
                row_count=int(payload.get("row_count", 0)),
                column_count=int(payload.get("column_count", 0)),
                contains_lingshan_records=bool(payload.get("contains_lingshan_records", False)),
                summary_json=json.dumps(payload, ensure_ascii=False),
            )
        ]
        return await self.behavior_summary_repository.replace_all(summaries)

    @staticmethod
    def _read_json(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _resolve_scenic_area(knowledge_payload: list[dict]) -> str:
        for item in knowledge_payload:
            metadata = item.get("metadata") or {}
            scenic_area = str(metadata.get("scenic_area", "")).strip()
            if scenic_area:
                return scenic_area
        return ""

    @staticmethod
    def _resolve_guide_document_name(knowledge_payload: list[dict], route_payload: list[dict]) -> str:
        for item in route_payload:
            source = str(item.get("source", "")).strip()
            if " - " in source:
                return source.split(" - ", 1)[0]
        for item in knowledge_payload:
            source = str(item.get("source", "")).strip()
            if "游览指南" in source and " - " in source:
                return source.split(" - ", 1)[0]
        return ""

    @staticmethod
    def _infer_guide_category(title: str) -> str:
        if "路线" in title:
            return "游览路线"
        if "贴士" in title or title in {"最佳游览时间", "餐饮", "住宿", "其他实用建议"}:
            return "实用贴士"
        if "景点" in title:
            return "景点解读"
        return "历史文化"

    @staticmethod
    def _infer_route_tags(route_payload: dict) -> list[str]:
        title = str(route_payload.get("title", ""))
        if "亲子" in title or "家庭" in title:
            return ["亲子", "家庭", "互动"]
        if "自然" in title or "风光" in title:
            return ["自然", "风光", "休闲"]
        if "历史" in title or "文化" in title:
            return ["历史", "文化", "朝圣"]
        return ["综合"]
