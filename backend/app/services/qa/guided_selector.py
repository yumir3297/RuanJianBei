from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from app.models.knowledge import KnowledgeEntry
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.repositories.route import RouteRepository
from app.schemas.chat import ConversationContext
from app.schemas.selection import SelectionContext
from app.services.rag.base import RetrievalScope


ResolutionSource = Literal["query", "selection", "history", "default"]

TOPIC_CATEGORY_MAP = {
    "attractions": "景点信息",
    "history": "历史文化",
    "routes": "游览路线",
    "family": "游览路线",
    "practical": "实用贴士",
    "dining": "实用贴士",
}


def build_selection_cache_key(
    normalized_query: str,
    selection: SelectionContext,
    *,
    answer_namespace: str = "default",
) -> str:
    payload = {
        "query": normalized_query,
        "mode": selection.mode,
        "attraction_id": selection.attraction_id,
        "topic_key": selection.topic_key,
        "route_id": selection.route_id,
        "answer_namespace": answer_namespace,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"qa:v3:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ResolvedInteraction:
    selection: SelectionContext
    scope: RetrievalScope | None
    resolution_source: ResolutionSource
    active_subject: str | None
    warnings: tuple[str, ...] = ()

    def to_event_data(self) -> dict:
        return {
            "selection": self.selection.model_dump(mode="json"),
            "conversation_context": {
                "last_subject": self.active_subject,
                "history_summary": None,
            },
            "resolution_source": self.resolution_source,
            "warnings": list(self.warnings),
        }


class GuidedSelectionResolver:
    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        quick_topic_repository: QuickTopicRepository,
        route_repository: RouteRepository,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.quick_topic_repository = quick_topic_repository
        self.route_repository = route_repository

    async def resolve(
        self,
        query: str,
        selection: SelectionContext | None,
        context: ConversationContext | None = None,
    ) -> ResolvedInteraction:
        requested = selection or SelectionContext()
        attractions = await self.knowledge_repository.list_by_category("景点信息")
        explicit_attraction = self._find_attraction(query, attractions)
        selected_attraction = await self._validate_attraction(requested.attraction_id)
        selected_topic = await self._validate_topic(requested.topic_key)
        selected_route = await self._validate_route(requested.route_id)
        warnings = self._validation_warnings(
            requested,
            selected_attraction=selected_attraction,
            selected_topic=selected_topic,
            selected_route=selected_route,
        )

        if explicit_attraction is not None:
            if selected_attraction is not None and selected_attraction.id != explicit_attraction.id:
                warnings.append("query_entity_overrode_selection")
            resolved = self._selection_from(
                requested,
                mode="attraction",
                attraction_id=explicit_attraction.id,
                topic_key=selected_topic.key if selected_topic is not None else None,
                route_id=None,
            )
            return ResolvedInteraction(
                selection=resolved,
                scope=RetrievalScope(source_entry_id=explicit_attraction.id),
                resolution_source="query",
                active_subject=explicit_attraction.title,
                warnings=tuple(warnings),
            )

        selected_result = await self._resolve_valid_selection(
            requested,
            selected_attraction=selected_attraction,
            selected_topic=selected_topic,
            selected_route=selected_route,
            warnings=warnings,
        )
        if selected_result is not None:
            return selected_result

        history_attraction = self._find_attraction(context.last_subject, attractions) if context else None
        if history_attraction is not None:
            resolved = self._selection_from(
                requested,
                mode="attraction",
                attraction_id=history_attraction.id,
                topic_key=None,
                route_id=None,
            )
            return ResolvedInteraction(
                selection=resolved,
                scope=RetrievalScope(source_entry_id=history_attraction.id),
                resolution_source="history",
                active_subject=history_attraction.title,
                warnings=tuple(warnings),
            )

        return ResolvedInteraction(
            selection=self._selection_from(
                requested,
                mode="free_chat",
                attraction_id=None,
                topic_key=None,
                route_id=None,
            ),
            scope=None,
            resolution_source="default",
            active_subject=None,
            warnings=tuple(warnings),
        )

    async def _resolve_valid_selection(
        self,
        requested: SelectionContext,
        *,
        selected_attraction,
        selected_topic,
        selected_route,
        warnings: list[str],
    ) -> ResolvedInteraction | None:
        if requested.mode == "attraction" and selected_attraction is not None:
            resolved = self._selection_from(
                requested,
                mode="attraction",
                attraction_id=selected_attraction.id,
                topic_key=selected_topic.key if selected_topic is not None else None,
                route_id=None,
            )
            return ResolvedInteraction(
                selection=resolved,
                scope=RetrievalScope(source_entry_id=selected_attraction.id),
                resolution_source="selection",
                active_subject=selected_attraction.title,
                warnings=tuple(warnings),
            )

        if requested.mode == "topic" and selected_topic is not None:
            resolved = self._selection_from(
                requested,
                mode="topic",
                attraction_id=None,
                topic_key=selected_topic.key,
                route_id=None,
            )
            category = TOPIC_CATEGORY_MAP.get(selected_topic.key)
            scope = RetrievalScope(category=category) if category else None
            return ResolvedInteraction(
                selection=resolved,
                scope=scope,
                resolution_source="selection",
                active_subject=selected_topic.label,
                warnings=tuple(warnings),
            )

        if requested.mode == "route" and selected_route is not None:
            resolved = self._selection_from(
                requested,
                mode="route",
                attraction_id=None,
                topic_key=None,
                route_id=selected_route.id,
            )
            route_entry = await self.knowledge_repository.find_route_overview(selected_route.title)
            scope = RetrievalScope(source_entry_id=route_entry.id) if route_entry is not None else RetrievalScope(category="游览路线")
            return ResolvedInteraction(
                selection=resolved,
                scope=scope,
                resolution_source="selection",
                active_subject=selected_route.title,
                warnings=tuple(warnings),
            )

        return None

    async def _validate_attraction(self, attraction_id: int | None) -> KnowledgeEntry | None:
        if attraction_id is None:
            return None
        return await self.knowledge_repository.get_attraction(attraction_id)

    async def _validate_topic(self, topic_key: str | None):
        if topic_key is None:
            return None
        return await self.quick_topic_repository.get_enabled(topic_key)

    async def _validate_route(self, route_id: str | None):
        if route_id is None:
            return None
        return await self.route_repository.get(route_id)

    @staticmethod
    def _validation_warnings(
        requested: SelectionContext,
        *,
        selected_attraction,
        selected_topic,
        selected_route,
    ) -> list[str]:
        warnings: list[str] = []
        if requested.attraction_id is not None and selected_attraction is None:
            warnings.append("invalid_attraction_id")
        if requested.topic_key is not None and selected_topic is None:
            warnings.append("invalid_topic_key")
        if requested.route_id is not None and selected_route is None:
            warnings.append("invalid_route_id")
        return warnings

    @staticmethod
    def _selection_from(
        requested: SelectionContext,
        *,
        mode: str,
        attraction_id: int | None,
        topic_key: str | None,
        route_id: str | None,
    ) -> SelectionContext:
        return SelectionContext(
            mode=mode,
            attraction_id=attraction_id,
            topic_key=topic_key,
            route_id=route_id,
            interests=requested.interests,
            audience_type=requested.audience_type,
            available_hours=requested.available_hours,
            avoid_crowded=requested.avoid_crowded,
        )

    @classmethod
    def _find_attraction(
        cls,
        text: str | None,
        attractions: list[KnowledgeEntry],
    ) -> KnowledgeEntry | None:
        normalized = (text or "").strip().casefold()
        if not normalized:
            return None

        matches: list[tuple[int, int, int, KnowledgeEntry]] = []
        for attraction in attractions:
            aliases = [item.strip() for item in attraction.aliases.split("|") if item.strip()]
            terms = {attraction.title.strip(), *aliases}
            for term in terms:
                folded = term.casefold()
                position = normalized.find(folded)
                if position >= 0:
                    matches.append((-len(folded), position, attraction.id, attraction))

        if not matches:
            return None
        matches.sort(key=lambda item: (item[0], item[1], item[2]))
        return matches[0][3]

    async def find_attraction_by_candidates(self, candidate_titles: list[str]) -> KnowledgeEntry | None:
        """用视觉识别的候选景点名匹配知识库中的真实景点。"""
        if not candidate_titles:
            return None
        attractions = await self.knowledge_repository.list_by_category("景点信息")
        for title in candidate_titles:
            if not isinstance(title, str) or not title.strip():
                continue
            entry = self._find_attraction(title.strip(), attractions)
            if entry is not None:
                return entry
        return None
