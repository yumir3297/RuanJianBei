from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_chunk import KnowledgeChunk


SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？!?；;])")


@dataclass(slots=True)
class ChunkingConfig:
    max_chars: int = 520
    overlap_chars: int = 80


class KnowledgeChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def build_chunks(self, entries: list[KnowledgeEntry]) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for entry in entries:
            entry_metadata = self._load_metadata(entry.metadata_json)
            entry_metadata.update(
                {
                    "source_entry_id": entry.id,
                    "source_title": entry.title,
                    "source_category": entry.category,
                    "source": entry.source,
                    "aliases": [item for item in entry.aliases.split("|") if item],
                }
            )

            for index, content in enumerate(self._split_text(entry.content), start=1):
                metadata = {**entry_metadata, "chunk_index": index}
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"ke_{entry.id}_{index:03d}",
                        source_entry_id=entry.id,
                        chunk_index=index,
                        title=entry.title,
                        category=entry.category,
                        content=content,
                        source=entry.source,
                        metadata_json=json.dumps(metadata, ensure_ascii=False),
                    )
                )
        return chunks

    def _split_text(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        if not normalized:
            return []
        if len(normalized) <= self.config.max_chars:
            return [normalized]

        sentences = [item.strip() for item in SENTENCE_BOUNDARY_RE.split(normalized) if item.strip()]
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if not current:
                current = sentence
                continue
            if len(current) + len(sentence) <= self.config.max_chars:
                current = f"{current}{sentence}"
                continue
            chunks.extend(self._split_oversized(current))
            overlap = current[-self.config.overlap_chars :] if self.config.overlap_chars else ""
            current = f"{overlap}{sentence}" if overlap else sentence

        if current:
            chunks.extend(self._split_oversized(current))

        return [chunk for chunk in chunks if chunk]

    def _split_oversized(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        if len(normalized) <= self.config.max_chars:
            return [normalized]

        chunks: list[str] = []
        step = max(1, self.config.max_chars - self.config.overlap_chars)
        for start in range(0, len(normalized), step):
            chunk = normalized[start : start + self.config.max_chars]
            if chunk:
                chunks.append(chunk)
            if start + self.config.max_chars >= len(normalized):
                break
        return chunks

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _load_metadata(metadata_json: str | None) -> dict:
        if not metadata_json:
            return {}
        try:
            loaded = json.loads(metadata_json)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
