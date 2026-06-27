from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_blind_spot import KnowledgeBlindSpot


class KnowledgeBlindSpotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, blind_spot_id: int) -> KnowledgeBlindSpot | None:
        return self.session.get(KnowledgeBlindSpot, blind_spot_id)

    def get_by_normalized_query(self, normalized_query: str) -> KnowledgeBlindSpot | None:
        stmt = select(KnowledgeBlindSpot).where(
            KnowledgeBlindSpot.normalized_query == normalized_query
        )
        return self.session.scalar(stmt)

    def list(self, *, status: str | None = None, limit: int = 50) -> list[KnowledgeBlindSpot]:
        stmt = select(KnowledgeBlindSpot)
        if status is not None:
            stmt = stmt.where(KnowledgeBlindSpot.status == status)
        stmt = stmt.order_by(
            KnowledgeBlindSpot.hit_count.desc(),
            KnowledgeBlindSpot.last_seen_at.desc(),
            KnowledgeBlindSpot.id.desc(),
        ).limit(limit)
        return list(self.session.scalars(stmt))

    def list_resolved_faq_ids(self) -> set[str]:
        stmt = select(KnowledgeBlindSpot.resolved_faq_id).where(
            KnowledgeBlindSpot.status == "resolved",
            KnowledgeBlindSpot.resolution_type == "faq",
            KnowledgeBlindSpot.resolved_faq_id.is_not(None),
        )
        return {faq_id for faq_id in self.session.scalars(stmt) if faq_id}

    def record(
        self,
        *,
        normalized_query: str,
        raw_query: str,
        category: str = "unknown",
        sample_limit: int = 5,
    ) -> KnowledgeBlindSpot:
        entry = self.get_by_normalized_query(normalized_query)
        now = datetime.now(timezone.utc)
        if entry is None:
            entry = KnowledgeBlindSpot(
                normalized_query=normalized_query,
                raw_query_samples_json=json.dumps([raw_query], ensure_ascii=False),
                hit_count=1,
                status="open",
                category=category,
                first_seen_at=now,
                last_seen_at=now,
            )
        else:
            samples = self.load_samples(entry.raw_query_samples_json)
            if raw_query not in samples:
                samples.append(raw_query)
                samples = samples[-sample_limit:]
            entry.raw_query_samples_json = json.dumps(samples, ensure_ascii=False)
            entry.hit_count += 1
            entry.last_seen_at = now

        self.session.add(entry)
        self.session.flush()
        return entry

    def mark_resolved_with_faq(
        self,
        entry: KnowledgeBlindSpot,
        *,
        faq_id: str,
        category: str,
    ) -> KnowledgeBlindSpot:
        entry.status = "resolved"
        entry.category = category
        entry.resolution_type = "faq"
        entry.resolved_faq_id = faq_id
        entry.resolved_knowledge_id = None
        entry.resolved_at = datetime.now(timezone.utc)
        self.session.add(entry)
        self.session.flush()
        return entry

    @staticmethod
    def load_samples(payload: str) -> list[str]:
        try:
            samples = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(samples, list):
            return []
        return [str(item) for item in samples if str(item).strip()]
