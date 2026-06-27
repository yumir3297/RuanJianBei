from __future__ import annotations

import json
from time import perf_counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories.faq import FAQRepository
from app.services.qa.faq_semantic_index import FAQSemanticIndex, FAQSemanticMatch
from app.services.qa.faq_semantic_gate import FAQSemanticGate
from app.services.rag.embedder import BaseEmbedder


@dataclass(slots=True)
class FAQEntry:
    id: str
    category: str
    aliases: list[str]
    answer: str
    sources: list[str]


@dataclass(slots=True)
class FAQMatchResult:
    is_hit: bool
    level: str = "none"
    entry: FAQEntry | None = None

    @property
    def answer(self) -> str:
        return self.entry.answer if self.entry else ""

    @property
    def sources(self) -> list[str]:
        return self.entry.sources if self.entry else []


class FAQMatcher:
    def __init__(self) -> None:
        self.entries: list[FAQEntry] = []
        self.exact_index: dict[str, FAQEntry] = {}
        self.semantic_index: FAQSemanticIndex | None = None
        self.semantic_gate = FAQSemanticGate()

    def clear(self) -> None:
        self.entries.clear()
        self.exact_index.clear()
        if self.semantic_index is not None:
            self.semantic_index.clear()
        self.semantic_gate.build([])

    def add(self, faq_entries: list[FAQEntry]) -> None:
        self.entries.extend(faq_entries)
        for entry in faq_entries:
            for alias in entry.aliases:
                self.exact_index[self._normalize(alias)] = entry
        self.semantic_gate.build(self.entries)

    def load_from_file(self, path: Path) -> None:
        if not path.exists():
            return
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        entries = [
            FAQEntry(
                id=item["id"],
                category=item["category"],
                aliases=item["aliases"],
                answer=item["answer"],
                sources=item.get("sources", []),
            )
            for item in raw_data
        ]
        self.add(entries)

    def load_from_db(self, session: Session) -> None:
        records = FAQRepository(session).list_all()
        entries = [
            FAQEntry(
                id=record.id,
                category=record.category,
                aliases=json.loads(record.aliases_json),
                answer=record.answer,
                sources=json.loads(record.sources_json),
            )
            for record in records
        ]
        self.add(entries)

    def reload(self, session: Session) -> float:
        start = perf_counter()
        self.clear()
        self.load_from_db(session)
        if self.semantic_index is not None:
            self.semantic_index.build(self.entries)
        return (perf_counter() - start) * 1000

    def ensure_semantic_index(self, embedder: BaseEmbedder, threshold: float) -> float:
        alias_count = sum(len(entry.aliases) for entry in self.entries)
        if (
            self.semantic_index is not None
            and self.semantic_index.model_name == embedder.model_name
            and self.semantic_index.threshold == threshold
            and self.semantic_index.alias_count == alias_count
        ):
            return 0.0

        self.semantic_index = FAQSemanticIndex(embedder, threshold)
        return self.semantic_index.build(self.entries)

    def match_exact(self, query: str) -> FAQEntry | None:
        return self.exact_index.get(self._normalize(query))

    def match_fuzzy(self, query: str) -> FAQEntry | None:
        normalized = self._normalize(query)
        best_score = 0.0
        best_entry: FAQEntry | None = None
        for entry in self.entries:
            for alias in entry.aliases:
                score = SequenceMatcher(None, normalized, self._normalize(alias)).ratio()
                if score > best_score:
                    best_score = score
                    best_entry = entry
        return best_entry if best_score >= 0.72 else None

    def match_semantic(self, query: str, embedding_fn=None) -> FAQSemanticMatch | None:
        del embedding_fn
        if self.semantic_index is None:
            return None
        decision = self.semantic_gate.decide(query)
        if not decision.allowed:
            return None
        return self.semantic_index.match(query, allowed_entry_ids=decision.allowed_entry_ids)

    def match(self, query: str, embedding_fn=None) -> FAQMatchResult:
        exact = self.match_exact(query)
        if exact:
            return FAQMatchResult(is_hit=True, level="exact", entry=exact)
        fuzzy = self.match_fuzzy(query)
        if fuzzy:
            return FAQMatchResult(is_hit=True, level="fuzzy", entry=fuzzy)
        semantic = self.match_semantic(query, embedding_fn)
        if semantic:
            return FAQMatchResult(is_hit=True, level="semantic", entry=semantic.entry)
        return FAQMatchResult(is_hit=False)

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(text.strip().lower().split())
