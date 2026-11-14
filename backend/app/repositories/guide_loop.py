from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_loop import GuideLoopCase, GuideLoopObservation, GuideLoopPointer
from app.schemas.guide_loop import ObservationCreate
from app.schemas.guide_loop import QuestionContext
from app.services.guide_loop.matching import match_pair


class GuideLoopRepository:
    def __init__(self, session: AsyncSession, *, now=None, retention_days: int = 14) -> None:
        self.session = session
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.retention_days = retention_days

    @staticmethod
    def _sibling_cluster_id(requested_cluster_id: str, discriminator: str) -> str:
        digest = hashlib.sha256(f"{requested_cluster_id}\0{discriminator}".encode()).hexdigest()[:16]
        return f"{requested_cluster_id[:76]}~{digest}"

    async def record(self, payload: ObservationCreate) -> tuple[GuideLoopObservation, bool]:
        await self.purge_expired()
        existing = await self.session.get(GuideLoopObservation, payload.event_id)
        if existing:
            same = (
                (existing.requested_cluster_id or existing.cluster_id) == payload.cluster_id
                and existing.session_key == payload.session_key
                and existing.text == payload.text
                and existing.queried_date == payload.queried_date
                and existing.poi_id == payload.poi_id
                and existing.target_id == payload.target_id
                and existing.unit_id == payload.unit_id
                and json.loads(existing.evidence_ids_json) == payload.evidence_ids
                and existing.result_code == payload.result_code
                and existing.category == payload.category
                and existing.replay_id == payload.replay_id
                and existing.origin == payload.origin
            )
            if not same:
                raise ValueError("event_id was already used for a different observation")
            return existing, True
        candidate = QuestionContext(
            text=payload.text,
            poi_id=payload.poi_id,
            target_id=payload.target_id,
            unit_id=payload.unit_id,
            queried_date=payload.queried_date.isoformat() if payload.queried_date else None,
        )
        self_decision = match_pair(candidate, candidate, 1.0, 0.0)
        target_cluster_id = payload.cluster_id
        match_decision = self_decision.decision
        reason_code = self_decision.reason_code if self_decision.decision == "clarify" else None
        if self_decision.decision == "clarify":
            target_cluster_id = self._sibling_cluster_id(payload.cluster_id, f"{self_decision.reason_code}:{payload.event_id}")

        existing_events = (await self.session.scalars(
            select(GuideLoopObservation).where(or_(
                GuideLoopObservation.requested_cluster_id == payload.cluster_id,
                GuideLoopObservation.cluster_id == payload.cluster_id,
            ))
        )).all()
        for event in existing_events:
            prior = QuestionContext(
                text=event.text,
                poi_id=event.poi_id,
                target_id=event.target_id,
                unit_id=event.unit_id,
                queried_date=event.queried_date.isoformat() if event.queried_date else None,
            )
            decision = match_pair(prior, candidate, 1.0, 0.0)
            if decision.decision == "reuse":
                target_cluster_id = event.cluster_id
                match_decision = decision.decision
                reason_code = decision.reason_code
                break
            if decision.decision == "distinct" and decision.reason_code in {"poi_conflict", "target_conflict"}:
                raise ValueError(f"observation conflicts with cluster scope: {decision.reason_code}")
            if decision.reason_code == "date_conflict":
                target_cluster_id = self._sibling_cluster_id(payload.cluster_id, f"date:{candidate.queried_date}")
                match_decision = decision.decision
                reason_code = decision.reason_code
            elif decision.decision == "clarify":
                target_cluster_id = self._sibling_cluster_id(payload.cluster_id, f"{decision.reason_code}:{payload.event_id}")
                match_decision = decision.decision
                reason_code = decision.reason_code

        case = await self.session.get(GuideLoopCase, target_cluster_id)
        now = self._now()
        if case is None:
            case = GuideLoopCase(cluster_id=target_cluster_id, category=payload.category, status="open", created_at=now, updated_at=now)
            self.session.add(case)
        elif case.category == "unknown" and payload.category != "unknown":
            case.category = payload.category
            case.updated_at = now
        observation = GuideLoopObservation(
            event_id=payload.event_id,
            cluster_id=target_cluster_id,
            requested_cluster_id=payload.cluster_id,
            session_key=payload.session_key,
            text=payload.text,
            queried_date=payload.queried_date,
            poi_id=payload.poi_id,
            target_id=payload.target_id,
            unit_id=payload.unit_id,
            evidence_ids_json=json.dumps(payload.evidence_ids, ensure_ascii=False),
            result_code=payload.result_code,
            category=payload.category,
            replay_id=payload.replay_id,
            origin=payload.origin,
            match_decision=match_decision,
            reason_code=reason_code,
            created_at=now,
        )
        self.session.add(observation)
        await self.session.flush()
        return observation, False

    async def purge_expired(self) -> int:
        cutoff = self._now() - timedelta(days=self.retention_days)
        result = await self.session.execute(
            delete(GuideLoopObservation).where(GuideLoopObservation.created_at < cutoff)
        )
        # Keep revision/audit cases; only remove empty, still-unprocessed cases.
        cases = (await self.session.scalars(select(GuideLoopCase).where(GuideLoopCase.status == "open"))).all()
        for case in cases:
            remaining = await self.session.scalar(
                select(func.count()).select_from(GuideLoopObservation).where(GuideLoopObservation.cluster_id == case.cluster_id)
            )
            if not remaining:
                await self.session.delete(case)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def list_cases(self) -> list[dict]:
        await self.purge_expired()
        cases = (await self.session.scalars(
            select(GuideLoopCase).where(GuideLoopCase.status != "closed").order_by(GuideLoopCase.updated_at.desc())
        )).all()
        output = []
        for case in cases:
            events = (await self.session.scalars(
                select(GuideLoopObservation).where(GuideLoopObservation.cluster_id == case.cluster_id).order_by(GuideLoopObservation.created_at.desc())
            )).all()
            draft = json.loads(case.draft_json) if case.draft_json else None
            active_revision_id = None
            if draft:
                pointer = await self.session.get(GuideLoopPointer, f"{draft['poi_id']}:{draft['target_id']}")
                active_revision_id = pointer.revision_id if pointer else None
            output.append({
                "cluster_id": case.cluster_id,
                "category": case.category,
                "status": case.status,
                "observation_count": len(events),
                "distinct_session_count": len({event.session_key for event in events}),
                "sample_questions": list(dict.fromkeys(event.text for event in events))[:5],
                "replay_ids": list(dict.fromkeys(event.replay_id for event in events)),
                "clarification_required": any(event.match_decision == "clarify" for event in events),
                "clarification_reasons": list(dict.fromkeys(event.reason_code for event in events if event.reason_code)),
                "draft_id": case.draft_id,
                "draft": draft,
                "verification": json.loads(case.verification_json) if case.verification_json else None,
                "active_revision_id": active_revision_id,
            })
        return output
