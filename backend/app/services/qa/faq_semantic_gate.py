from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.qa.faq_matcher import FAQEntry


SPOT_INTENT_BY_CATEGORY = {
    "景点介绍": "introduction",
    "景点位置": "location",
    "景点参数": "parameters",
    "开放信息": "opening",
}

UNSUPPORTED_TERMS = (
    "卫生间",
    "厕所",
    "停车",
    "天气",
    "下雨",
    "门票多少钱",
    "票价",
    "公交",
    "火车站",
    "客流",
    "身份证",
    "无线网络",
    "wifi",
    "充电宝",
    "宠物",
    "医务室",
    "股票",
)

INTENT_TERMS = {
    "parameters": ("参数", "尺寸", "规模", "多高", "多宽", "多长", "多大", "高度", "宽度", "重量", "面积"),
    "opening": ("开放", "开门", "关门", "几点", "什么时候可以", "可以进去", "能参观", "停止参观"),
    "location": ("位置", "哪里", "哪儿", "哪个地方", "哪个区域", "怎么走", "往哪里走", "什么地方"),
    "introduction": ("介绍", "是什么", "特色", "亮点", "看点", "好玩", "值得看", "内容", "体验"),
}


@dataclass(frozen=True, slots=True)
class FAQSemanticGateDecision:
    allowed_entry_ids: frozenset[str]
    entity: str | None
    intent: str | None
    reason: str

    @property
    def allowed(self) -> bool:
        return bool(self.allowed_entry_ids)


class FAQSemanticGate:
    def __init__(self) -> None:
        self._spot_entries: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._global_entries: dict[str, set[str]] = defaultdict(set)
        self._entity_terms: list[tuple[str, str]] = []

    def build(self, entries: list[FAQEntry]) -> None:
        self._spot_entries.clear()
        self._global_entries.clear()
        entities: set[str] = set()

        for entry in entries:
            intent = SPOT_INTENT_BY_CATEGORY.get(entry.category)
            if intent:
                entity = self._extract_entry_entity(entry)
                if entity:
                    entities.add(entity)
                    self._spot_entries[(entity, intent)].add(entry.id)
                continue
            if entry.category == "景区概况":
                self._global_entries["overview"].add(entry.id)
            elif entry.category == "游览贴士":
                self._global_entries["visit_time"].add(entry.id)

        term_owners: dict[str, set[str]] = defaultdict(set)
        for entity in entities:
            term_owners[entity].add(entity)
            for start in range(1, len(entity) - 1):
                suffix = entity[start:]
                if len(suffix) >= 2:
                    term_owners[suffix].add(entity)

        self._entity_terms = sorted(
            [
                (term, next(iter(owners)))
                for term, owners in term_owners.items()
                if len(owners) == 1
            ],
            key=lambda item: len(item[0]),
            reverse=True,
        )

    def decide(self, query: str) -> FAQSemanticGateDecision:
        normalized = "".join(query.strip().lower().split())
        if not normalized:
            return FAQSemanticGateDecision(frozenset(), None, None, "empty_query")
        if any(term in normalized for term in UNSUPPORTED_TERMS):
            return FAQSemanticGateDecision(frozenset(), None, None, "unsupported_domain")

        entity = self._find_entity(normalized)
        if entity:
            intent = self._classify_spot_intent(normalized)
            if intent is None:
                return FAQSemanticGateDecision(frozenset(), entity, None, "unknown_spot_intent")
            ids = frozenset(self._spot_entries.get((entity, intent), set()))
            return FAQSemanticGateDecision(ids, entity, intent, "spot_entity_and_intent")

        if self._is_visit_time_query(normalized):
            return FAQSemanticGateDecision(
                frozenset(self._global_entries.get("visit_time", set())),
                None,
                "visit_time",
                "global_visit_time",
            )
        if self._is_overview_query(normalized):
            return FAQSemanticGateDecision(
                frozenset(self._global_entries.get("overview", set())),
                None,
                "overview",
                "global_overview",
            )
        return FAQSemanticGateDecision(frozenset(), None, None, "no_trusted_entity_or_intent")

    @staticmethod
    def _extract_entry_entity(entry: FAQEntry) -> str | None:
        suffixes = {
            "介绍",
            "是什么",
            "有什么亮点",
            "位置",
            "在哪里",
            "建筑参数",
            "有什么参数",
            "有多高",
            "多高",
            "高度多少",
            "什么时候开放",
            "开放时间",
        }
        candidates: list[str] = []
        for alias in entry.aliases:
            normalized = "".join(alias.strip().split())
            for suffix in sorted(suffixes, key=len, reverse=True):
                if normalized.endswith(suffix):
                    entity = normalized[: -len(suffix)]
                    if len(entity) >= 2:
                        candidates.append(entity)
                    break
        if not candidates:
            return None
        counts = Counter(candidates)
        return max(counts, key=lambda item: (counts[item], len(item)))

    def _find_entity(self, query: str) -> str | None:
        for term, entity in self._entity_terms:
            if term in query:
                return entity
        return None

    @staticmethod
    def _classify_spot_intent(query: str) -> str | None:
        for intent in ("parameters", "opening", "location", "introduction"):
            if any(term in query for term in INTENT_TERMS[intent]):
                return intent
        return None

    @staticmethod
    def _is_visit_time_query(query: str) -> bool:
        return any(term in query for term in ("最佳游览时间", "什么时候去最好", "哪个季节", "什么季节", "季节来", "游玩比较舒服"))

    @staticmethod
    def _is_overview_query(query: str) -> bool:
        if "灵山胜境" not in query and "这个景区" not in query:
            return False
        return any(term in query for term in ("介绍", "是什么景区", "在哪里", "概况"))
