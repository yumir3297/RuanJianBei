from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Mapping
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tour_session import (
    TourArtifactReference,
    TourSession,
    TourSessionEvent,
    TourSessionIdempotency,
    TourSessionRevision,
    TourProgressRecord, TourProgressEvent, ItineraryProposal,
)
from app.schemas.itinerary import TourSnapshotV2
from app.services.itinerary.catalog import PublishedAttraction
from app.services.itinerary.progress import (
    ProgressCommand, ProgressConflict, TourProgress as V01Progress,
    apply_progress_command, start_tour, validate_remaining_budget,
)
from app.services.itinerary.provenance import normalize_snapshot_provenance

TRASH_DAYS = 30
IDEMPOTENCY_DAYS = 7


class RevisionConflict(Exception):
    def __init__(self, current_version: int | None) -> None:
        self.current_version = current_version
        super().__init__("游览内容已在其他位置更新")


class IdempotencyConflict(Exception):
    pass


def _encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_encode(value).encode("utf-8")).hexdigest()


def _decode(value: str) -> dict:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class TourSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _replay(self, owner_id: str, endpoint: str, key: str, payload: object) -> dict | None:
        if not key or len(key) > 128:
            raise ValueError("幂等键长度必须为 1 到 128 个字符")
        record = await self.session.scalar(select(TourSessionIdempotency).where(
            TourSessionIdempotency.owner_id == owner_id,
            TourSessionIdempotency.endpoint == endpoint,
            TourSessionIdempotency.key == key,
        ))
        if record is None:
            return None
        if _aware(record.expires_at) <= datetime.now(UTC):
            await self.session.delete(record)
            await self.session.flush()
            return None
        if record.payload_digest != _digest(payload):
            raise IdempotencyConflict("幂等键已用于不同内容")
        return _decode(record.response_json)

    def _remember(
        self, owner_id: str, endpoint: str, key: str, payload: object,
        response: dict, session_id: str | None = None,
    ) -> None:
        self.session.add(TourSessionIdempotency(
            id=str(uuid4()), owner_id=owner_id, endpoint=endpoint, key=key,
            session_id=session_id,
            payload_digest=_digest(payload), response_json=_encode(response),
            expires_at=datetime.now(UTC) + timedelta(days=IDEMPOTENCY_DAYS),
        ))

    def _add_event(self, session_id: str, event_type: str, version: int, payload: dict | None = None) -> None:
        self.session.add(TourSessionEvent(
            id=str(uuid4()), session_id=session_id, event_type=event_type,
            version=version, payload_json=_encode(payload or {}), created_at=datetime.now(UTC),
        ))

    async def _commit_with_replay(self, owner_id: str, endpoint: str, key: str, payload: object) -> dict | None:
        try:
            await self.session.commit()
            return None
        except IntegrityError:
            await self.session.rollback()
            replay = await self._replay(owner_id, endpoint, key, payload)
            if replay is None:
                raise
            return replay

    async def _reconcile_progress_for_plan_change(
        self, session_id: str, before_raw: dict, after_raw: dict, row: TourProgressRecord,
    ) -> None:
        before, after = TourSnapshotV2.model_validate(before_raw), TourSnapshotV2.model_validate(after_raw)
        progress = V01Progress.model_validate(_decode(row.progress_json))
        if (progress.status == "active" and
                before.constraints.available_minutes != after.constraints.available_minutes):
            raise ValueError("游览进行中暂不支持修改总时长；当前截止时间保持不变")
        states = progress.status_by_stop
        old_stops, new_stops = {str(s.stop_id): s for s in before.stops}, {str(s.stop_id): s for s in after.stops}
        old_order, new_order = [str(s.stop_id) for s in before.stops], [str(s.stop_id) for s in after.stops]
        for stop_id, state in states.items():
            if state in {"completed", "skipped"} and (
                stop_id not in new_stops or old_stops.get(stop_id) != new_stops[stop_id]
                or old_order.index(stop_id) != new_order.index(stop_id)
            ):
                raise ValueError("已完成或跳过的游览记录不能通过行程编辑覆盖")
        if progress.current_stop_id is None and progress.status == "active":
            raise ValueError("当前游览进度缺少停留点，不能修改行程")
        if progress.current_stop_id and str(progress.current_stop_id) not in new_stops:
            raise ValueError("当前游览点不能在进行中移除")
        if progress.status == "active":
            current_index = new_order.index(str(progress.current_stop_id))
            if any(states.get(stop_id, "pending") == "pending" and index < current_index
                   for index, stop_id in enumerate(new_order)):
                raise ValueError("当前点之前不能插入待游览停留点")
            reconciled = {stop_id: states.get(stop_id, "pending") for stop_id in new_order}
            next_version = progress.progress_version + 1
            updated = progress.model_copy(update={"status_by_stop": reconciled, "progress_version": next_version})
            updated = V01Progress.model_validate(updated.model_dump(mode="python"))
            changed = await self.session.execute(update(TourProgressRecord).where(
                TourProgressRecord.session_id == session_id,
                TourProgressRecord.progress_version == progress.progress_version,
            ).values(progress_version=next_version, progress_json=_encode(updated.model_dump(mode="json")), updated_at=func.now()))
            if changed.rowcount != 1:
                await self.session.rollback()
                raise ProgressConflict("游览进度已变化，请刷新后再保存行程")
            self.session.add(TourProgressEvent(
                id=str(uuid4()), session_id=session_id, version=next_version,
                event_type="plan_reconciled", stop_id=None, payload_json="{}", occurred_at=datetime.now(UTC),
            ))
        else:
            changed = await self.session.execute(update(TourProgressRecord).where(
                TourProgressRecord.session_id == session_id,
                TourProgressRecord.progress_version == row.progress_version,
            ).values(updated_at=func.now()))
            if changed.rowcount != 1:
                await self.session.rollback()
                raise ProgressConflict("游览进度已变化，请刷新后再保存行程")

    async def _session_result(self, item: TourSession, revision: TourSessionRevision | None = None) -> dict:
        if revision is None:
            revision = await self.session.scalar(select(TourSessionRevision).where(
                TourSessionRevision.session_id == item.id,
                TourSessionRevision.version == item.version,
            ))
        return {
            "id": item.id,
            "site_id": item.site_id,
            "title": item.title,
            "status": item.status,
            "version": item.version,
            "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
            "deleted_until": item.deleted_until.isoformat() if item.deleted_until else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "revision_id": revision.id if revision else None,
            "snapshot": _decode(revision.snapshot_json) if revision else {},
        }

    async def create_session(
        self, owner_id: str, site_id: str, title: str, payload: dict, idempotency_key: str
    ) -> dict:
        request = {"site_id": site_id, "title": title, "snapshot": payload}
        replay = await self._replay(owner_id, "create", idempotency_key, request)
        if replay is not None:
            return replay
        item = TourSession(id=str(uuid4()), owner_id=owner_id, site_id=site_id,
                           title=title.strip() or "我的游览", status="draft", version=1)
        revision = TourSessionRevision(id=str(uuid4()), session_id=item.id, version=1,
                                       snapshot_json=_encode(payload))
        self.session.add_all([item, revision])
        self._add_event(item.id, "created", 1)
        await self.session.flush()
        result = await self._session_result(item, revision)
        self._remember(owner_id, "create", idempotency_key, request, result, item.id)
        replay = await self._commit_with_replay(owner_id, "create", idempotency_key, request)
        if replay is not None:
            return replay
        return result

    async def save_revision(
        self, owner_id: str, session_id: str, expected_version: int, payload: dict,
        idempotency_key: str, event_type: str = "saved", allow_upgrade: bool = False,
        catalog_entries: Mapping[str, PublishedAttraction] | None = None,
    ) -> dict:
        request = {"session_id": session_id, "expected_version": expected_version, "snapshot": payload}
        replay = await self._replay(owner_id, "save", idempotency_key, request)
        if replay is not None:
            return replay
        old_revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id, TourSessionRevision.version == expected_version,
        ))
        item_status = await self.session.scalar(select(TourSession.status).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.deleted_at.is_(None),
        ))
        if item_status is None:
            current = await self.session.scalar(select(TourSession.version).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id,
                TourSession.deleted_at.is_(None),
            ))
            if current is None:
                return None
            raise RevisionConflict(int(current))
        old_raw = _decode(old_revision.snapshot_json) if old_revision else {}
        old_v2 = old_raw.get("schema_version") == 2
        new_v2 = payload.get("schema_version") == 2
        if old_v2 != new_v2 and not allow_upgrade:
            raise ValueError("V2 行程必须通过 V2 接口保存，不能降级覆盖")
        if allow_upgrade and (old_v2 or not new_v2):
            raise ValueError("仅能把旧版行程升级为 V2")
        if old_v2 and new_v2:
            before_snapshot = TourSnapshotV2.model_validate(old_raw)
            normalized = normalize_snapshot_provenance(
                TourSnapshotV2.model_validate(payload), previous=before_snapshot,
                catalog_entries=catalog_entries,
            )
            payload = normalized.model_dump(mode="json")
            self._validate_locked_fields(old_raw, payload)
        progress_row = await self.session.get(TourProgressRecord, session_id)
        if progress_row is not None and old_v2:
            await self._reconcile_progress_for_plan_change(session_id, old_raw, payload, progress_row)
        result = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.status == item_status,
            TourSession.deleted_at.is_(None),
        ).values(version=expected_version + 1, updated_at=func.now()))
        if result.rowcount != 1:
            current = await self.session.scalar(select(TourSession.version).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id,
                TourSession.deleted_at.is_(None),
            ))
            await self.session.rollback()
            replay = await self._replay(owner_id, "save", idempotency_key, request)
            if replay is not None:
                return replay
            if current is None:
                return None
            raise RevisionConflict(int(current))
        revision = TourSessionRevision(id=str(uuid4()), session_id=session_id,
                                       version=expected_version + 1, snapshot_json=_encode(payload))
        self.session.add(revision)
        self._add_event(session_id, event_type, expected_version + 1)
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).mark_target_revision_changed(
            session_id, expected_version + 1,
        )
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        result_payload = await self._session_result(item, revision)
        self._remember(owner_id, "save", idempotency_key, request, result_payload, session_id)
        replay = await self._commit_with_replay(owner_id, "save", idempotency_key, request)
        if replay is not None:
            return replay
        return result_payload

    @staticmethod
    def _validate_locked_fields(before_raw: dict, after_raw: dict) -> None:
        before = TourSnapshotV2.model_validate(before_raw)
        after = TourSnapshotV2.model_validate(after_raw)
        before_by_id = {str(stop.stop_id): stop for stop in before.stops}
        after_by_id = {str(stop.stop_id): stop for stop in after.stops}
        old_positions = {str(stop.stop_id): index for index, stop in enumerate(before.stops)}
        new_positions = {str(stop.stop_id): index for index, stop in enumerate(after.stops)}
        for stop_id, old_stop in before_by_id.items():
            locks = set(old_stop.locked_fields)
            if not locks:
                continue
            new_stop = after_by_id.get(stop_id)
            if new_stop is None:
                raise ValueError("已锁定的停留点不能删除")
            if "stop" in locks and old_stop.model_copy(update={"locked_fields": []}) != new_stop.model_copy(update={"locked_fields": []}):
                raise ValueError("停留点已锁定，不能修改内容")
            if "position" in locks and old_positions[stop_id] != new_positions[stop_id]:
                raise ValueError("停留点顺序已锁定，不能移动")
            for field in locks & {"name", "spot_code", "duration"}:
                attr = "duration_minutes" if field == "duration" else field
                if getattr(old_stop, attr) != getattr(new_stop, attr):
                    raise ValueError(f"停留点的{field}字段已锁定，不能修改")

    async def get_progress(self, owner_id: str, session_id: str) -> dict | None:
        owned = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id, TourSession.deleted_at.is_(None),
        ))
        if owned is None:
            return None
        row = await self.session.get(TourProgressRecord, session_id)
        return _decode(row.progress_json) if row else None

    async def start_progress(self, owner_id: str, session_id: str, expected_version: int,
                             idempotency_key: str, now: datetime | None = None) -> dict | None:
        request = {"session_id": session_id, "expected_version": expected_version}
        replay = await self._replay(owner_id, "progress_start", idempotency_key, request)
        if replay is not None:
            return replay
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id, TourSession.deleted_at.is_(None),
        ))
        if item is None:
            return None
        revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id, TourSessionRevision.version == item.version,
        ))
        raw = _decode(revision.snapshot_json) if revision else {}
        if raw.get("schema_version") != 2:
            raise ValueError("开始游览前请先升级到 V2 行程")
        existing = await self.session.get(TourProgressRecord, session_id)
        if existing:
            return _decode(existing.progress_json)
        when = now or datetime.now(UTC)
        snapshot = TourSnapshotV2.model_validate(raw)
        budget = validate_remaining_budget(snapshot, None, when)
        if budget.status == "conflict":
            raise ProgressConflict(budget.message)
        transition = start_tour(snapshot, plan_version=item.version, expected_plan_version=expected_version, now=when)
        changed = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.status == "draft", TourSession.deleted_at.is_(None),
        ).values(status="active", updated_at=func.now()))
        if changed.rowcount != 1:
            await self.session.rollback()
            current = await self.session.scalar(select(TourSession.version).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id,
            ))
            if current is None:
                return None
            raise RevisionConflict(int(current))
        result = transition.progress.model_dump(mode="json")
        self.session.add(TourProgressRecord(
            session_id=session_id, progress_version=transition.progress.progress_version,
            progress_json=_encode(result),
        ))
        self.session.add(TourProgressEvent(
            id=str(uuid4()), session_id=session_id, version=transition.event.version,
            event_type=transition.event.event_type,
            stop_id=str(transition.event.stop_id) if transition.event.stop_id else None,
            payload_json="{}", occurred_at=transition.event.occurred_at,
        ))
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).mark_target_progress_changed(
            session_id, transition.progress.progress_version,
        )
        self._remember(owner_id, "progress_start", idempotency_key, request, result, session_id)
        replay = await self._commit_with_replay(owner_id, "progress_start", idempotency_key, request)
        return replay if replay is not None else result

    async def command_progress(self, owner_id: str, session_id: str, expected_progress_version: int,
                               command: ProgressCommand, idempotency_key: str,
                               now: datetime | None = None) -> dict | None:
        request = {"session_id": session_id, "expected_progress_version": expected_progress_version,
                   "command": command.model_dump(mode="json")}
        replay = await self._replay(owner_id, "progress_command", idempotency_key, request)
        if replay is not None:
            return replay
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id, TourSession.deleted_at.is_(None),
        ))
        if item is None:
            return None
        revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id, TourSessionRevision.version == item.version,
        ))
        raw = _decode(revision.snapshot_json) if revision else {}
        if raw.get("schema_version") != 2:
            raise ValueError("此游览不包含 V2 行程")
        row = await self.session.get(TourProgressRecord, session_id)
        if row is None:
            raise ProgressConflict("游览尚未开始")
        progress = V01Progress.model_validate(_decode(row.progress_json))
        transition = apply_progress_command(
            progress, TourSnapshotV2.model_validate(raw), expected_progress_version=expected_progress_version,
            command=command, now=now,
        )
        session_fence = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == item.version, TourSession.deleted_at.is_(None),
        ).values(updated_at=func.now(), status="completed" if transition.progress.status == "finished" else item.status))
        if session_fence.rowcount != 1:
            await self.session.rollback()
            raise RevisionConflict(item.version)
        changed = await self.session.execute(update(TourProgressRecord).where(
            TourProgressRecord.session_id == session_id,
            TourProgressRecord.progress_version == expected_progress_version,
        ).values(progress_version=transition.progress.progress_version,
                 progress_json=_encode(transition.progress.model_dump(mode="json")), updated_at=func.now()))
        if changed.rowcount != 1:
            await self.session.rollback()
            raise ProgressConflict("游览进度已在其他位置更新")
        event = transition.event
        self.session.add(TourProgressEvent(
            id=str(uuid4()), session_id=session_id, version=event.version, event_type=event.event_type,
            stop_id=str(event.stop_id) if event.stop_id else None, payload_json="{}", occurred_at=event.occurred_at,
        ))
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).mark_target_progress_changed(
            session_id, transition.progress.progress_version,
        )
        result = transition.progress.model_dump(mode="json")
        self._remember(owner_id, "progress_command", idempotency_key, request, result, session_id)
        replay = await self._commit_with_replay(owner_id, "progress_command", idempotency_key, request)
        return replay if replay is not None else result

    async def list_progress_events(self, owner_id: str, session_id: str) -> list[dict] | None:
        owned = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        if owned is None:
            return None
        rows = (await self.session.scalars(select(TourProgressEvent).where(
            TourProgressEvent.session_id == session_id,
        ).order_by(TourProgressEvent.version))).all()
        return [{"version": e.version, "event_type": e.event_type, "stop_id": e.stop_id,
                 "payload": _decode(e.payload_json), "occurred_at": e.occurred_at.isoformat()} for e in rows]

    @staticmethod
    def _proposal_payload(row: ItineraryProposal) -> dict:
        return {"id": row.id, "session_id": row.session_id, "base_version": row.base_version,
            "progress_version": row.progress_version, "draft_digest": row.draft_digest,
            "catalog_digest": row.catalog_digest, "status": row.status, "request_text": row.request_text,
            "base_snapshot": _decode(row.base_snapshot_json), "execution_job_id": row.execution_job_id,
            "operations": json.loads(row.operations_json), "candidate": json.loads(row.candidate_json),
            "diff": json.loads(row.diff_json), "validation": json.loads(row.validation_json),
            "clarification": row.clarification, "expires_at": row.expires_at.isoformat(),
            "applied_revision_id": row.applied_revision_id}

    async def reserve_proposal(self, owner_id: str, session_id: str, base_version: int, progress_version: int,
            draft_digest: str, catalog_digest: str, text: str, draft_snapshot: dict,
            idempotency_key: str, *, commit: bool = True) -> tuple[dict, bool]:
        request = {"session_id": session_id, "base_version": base_version, "progress_version": progress_version,
            "draft_digest": draft_digest, "catalog_digest": catalog_digest, "text": text}
        replay = await self._replay(owner_id, "proposal_create", idempotency_key, request)
        if replay is not None:
            return replay, False
        now = datetime.now(UTC)
        row = ItineraryProposal(id=str(uuid4()), owner_id=owner_id, session_id=session_id,
            base_version=base_version, progress_version=progress_version, draft_digest=draft_digest,
            catalog_digest=catalog_digest, status="executing", request_text=text,
            base_snapshot_json=_encode(draft_snapshot),
            operations_json="[]", candidate_json=_encode(draft_snapshot), diff_json="[]",
            validation_json=_encode({"status": "executing", "conflicts": []}),
            expires_at=now + timedelta(minutes=30))
        self.session.add(row)
        await self.session.flush()
        result = self._proposal_payload(row)
        self._remember(owner_id, "proposal_create", idempotency_key, request, result, session_id)
        if commit:
            replay = await self._commit_with_replay(owner_id, "proposal_create", idempotency_key, request)
            return (replay, False) if replay is not None else (result, True)
        await self.session.flush()
        return result, True

    async def find_proposal_replay(
        self, owner_id: str, session_id: str, base_version: int, progress_version: int,
        draft_digest: str, catalog_digest: str, text: str, idempotency_key: str,
    ) -> dict | None:
        request = {
            "session_id": session_id, "base_version": base_version,
            "progress_version": progress_version, "draft_digest": draft_digest,
            "catalog_digest": catalog_digest, "text": text,
        }
        replay = await self._replay(owner_id, "proposal_create", idempotency_key, request)
        if replay is None:
            return None
        return await self.get_proposal(owner_id, session_id, replay["id"])

    async def complete_reserved_proposal(self, owner_id: str, session_id: str, proposal_id: str,
            generated: dict, idempotency_key: str, *, commit: bool = True) -> dict:
        row = await self.session.scalar(select(ItineraryProposal).where(
            ItineraryProposal.id == proposal_id, ItineraryProposal.session_id == session_id,
            ItineraryProposal.owner_id == owner_id))
        if row is None:
            raise ValueError("行程提案不存在")
        if row.status != "executing":
            return self._proposal_payload(row)
        row.status = generated["status"]
        row.operations_json = _encode(generated["operations"])
        row.candidate_json = _encode(generated["candidate"])
        row.diff_json = _encode(generated["diff"])
        row.validation_json = _encode(generated["validation"])
        row.clarification = generated.get("clarification")
        result = self._proposal_payload(row)
        idem = await self.session.scalar(select(TourSessionIdempotency).where(
            TourSessionIdempotency.owner_id == owner_id,
            TourSessionIdempotency.endpoint == "proposal_create",
            TourSessionIdempotency.key == idempotency_key,
        ))
        if idem is not None:
            idem.response_json = _encode(result)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return result

    async def fail_reserved_proposal(self, owner_id: str, session_id: str, proposal_id: str,
            message: str, idempotency_key: str) -> dict | None:
        row = await self.session.scalar(select(ItineraryProposal).where(
            ItineraryProposal.id == proposal_id, ItineraryProposal.session_id == session_id,
            ItineraryProposal.owner_id == owner_id))
        if row is None:
            return None
        row.status = "failed"
        row.validation_json = _encode({"status": "failed", "message": message})
        result = self._proposal_payload(row)
        idem = await self.session.scalar(select(TourSessionIdempotency).where(
            TourSessionIdempotency.owner_id == owner_id,
            TourSessionIdempotency.endpoint == "proposal_create",
            TourSessionIdempotency.key == idempotency_key,
        ))
        if idem is not None:
            idem.response_json = _encode(result)
        await self.session.commit()
        return result

    async def create_proposal(self, owner_id: str, session_id: str, base_version: int, progress_version: int,
            draft_digest: str, catalog_digest: str, text: str, generated: dict, idempotency_key: str) -> dict:
        # Keep a direct helper for deterministic repository callers and tests.
        request = {"session_id": session_id, "base_version": base_version, "progress_version": progress_version,
            "draft_digest": draft_digest, "catalog_digest": catalog_digest, "text": text}
        replay = await self._replay(owner_id, "proposal_create", idempotency_key, request)
        if replay is not None: return replay
        row = ItineraryProposal(id=str(uuid4()), owner_id=owner_id, session_id=session_id,
            base_version=base_version, progress_version=progress_version, draft_digest=draft_digest,
            catalog_digest=catalog_digest, status=generated["status"], request_text=text,
            base_snapshot_json=_encode(generated.get("base_snapshot", generated["candidate"])),
            operations_json=_encode(generated["operations"]), candidate_json=_encode(generated["candidate"]),
            diff_json=_encode(generated["diff"]), validation_json=_encode(generated["validation"]),
            clarification=generated.get("clarification"), expires_at=datetime.now(UTC) + timedelta(minutes=30))
        self.session.add(row)
        await self.session.flush()
        result = self._proposal_payload(row)
        self._remember(owner_id, "proposal_create", idempotency_key, request, result, session_id)
        replay = await self._commit_with_replay(owner_id, "proposal_create", idempotency_key, request)
        return replay if replay is not None else result

    async def get_proposal(self, owner_id: str, session_id: str, proposal_id: str) -> dict | None:
        row = await self.session.scalar(select(ItineraryProposal).where(
            ItineraryProposal.id == proposal_id, ItineraryProposal.session_id == session_id,
            ItineraryProposal.owner_id == owner_id))
        if row is None:
            return None
        result = self._proposal_payload(row)
        if row.execution_job_id:
            from app.models.tool_execution import ToolJob

            job = await self.session.get(ToolJob, row.execution_job_id)
            if job is not None:
                result["execution_status"] = job.status
                if job.status in ("queued", "retry_wait", "running"):
                    result["status"] = "executing"
                elif job.status == "waiting_user":
                    result["status"] = "waiting_user"
                    result["validation"] = {"status": "waiting_user", "message": "外部 AI 调用结果不确定；确认可能重复调用后可重试。"}
                elif job.status in ("failed", "stale", "cancelled"):
                    result["status"] = "failed"
                    messages = {
                        "failed": "提案未能完成，请重新生成。",
                        "stale": "游览或进度已更新，请重新生成提案。",
                        "cancelled": "提案任务已取消。",
                    }
                    result["validation"] = {"status": "failed", "message": messages[job.status]}
        return result

    async def list_proposals(self, owner_id: str, session_id: str, limit: int = 10) -> list[dict] | None:
        owned = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.deleted_at.is_(None),
        ))
        if owned is None:
            return None
        limit = max(1, min(limit, 20))
        rows = (await self.session.scalars(select(ItineraryProposal).where(
            ItineraryProposal.owner_id == owner_id, ItineraryProposal.session_id == session_id,
        ).order_by(ItineraryProposal.created_at.desc(), ItineraryProposal.id.desc()).limit(limit))).all()
        summaries = []
        for row in rows:
            proposal = await self.get_proposal(owner_id, session_id, row.id)
            if proposal is not None:
                summaries.append({
                    "id": proposal["id"], "session_id": proposal["session_id"],
                    "status": proposal["status"], "execution_status": proposal.get("execution_status"),
                    "execution_job_id": proposal.get("execution_job_id"),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
        return summaries

    async def apply_proposal(self, owner_id: str, session_id: str, proposal_id: str,
            expected_version: int, progress_version: int, draft_digest: str, idempotency_key: str,
            catalog_entries: Mapping[str, PublishedAttraction] | None = None) -> dict | None:
        request = {"session_id": session_id, "proposal_id": proposal_id, "expected_version": expected_version,
            "progress_version": progress_version, "draft_digest": draft_digest}
        replay = await self._replay(owner_id, "proposal_apply", idempotency_key, request)
        if replay is not None: return replay
        proposal = await self.session.scalar(select(ItineraryProposal).where(
            ItineraryProposal.id == proposal_id, ItineraryProposal.session_id == session_id,
            ItineraryProposal.owner_id == owner_id))
        if proposal is None: return None
        if proposal.status != "ready" or _aware(proposal.expires_at) <= datetime.now(UTC):
            raise ValueError("提案已过期、需要澄清或已应用")
        if (proposal.base_version != expected_version or proposal.progress_version != progress_version
                or proposal.draft_digest != draft_digest):
            raise ValueError("草稿或游览进度已变化，请重新生成提案")
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id, TourSession.deleted_at.is_(None)))
        if item is None: return None
        if item.version != expected_version:
            await self.session.rollback()
            raise RevisionConflict(item.version)
        current_revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id, TourSessionRevision.version == item.version))
        current_raw = _decode(current_revision.snapshot_json) if current_revision else {}
        candidate = json.loads(proposal.candidate_json)
        if current_raw.get("schema_version") == 2 and candidate.get("schema_version") == 2:
            candidate = normalize_snapshot_provenance(
                TourSnapshotV2.model_validate(candidate),
                previous=TourSnapshotV2.model_validate(current_raw),
                catalog_entries=catalog_entries,
                new_stop_created_by="ai",
            ).model_dump(mode="json")
            self._validate_locked_fields(current_raw, candidate)
        progress = await self.session.get(TourProgressRecord, session_id)
        if (progress.progress_version if progress else 0) != progress_version:
            await self.session.rollback()
            raise ValueError("游览进度已变化，请重新生成提案")
        if progress is not None and current_raw.get("schema_version") == 2:
            await self._reconcile_progress_for_plan_change(session_id, current_raw, candidate, progress)
        elif progress is not None:
            fenced = await self.session.execute(update(TourProgressRecord).where(
                TourProgressRecord.session_id == session_id,
                TourProgressRecord.progress_version == progress_version,
            ).values(updated_at=func.now()))
            if fenced.rowcount != 1:
                await self.session.rollback()
                raise ValueError("游览进度已变化，请重新生成提案")
        changed = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.status == item.status,
            TourSession.deleted_at.is_(None),
        ).values(version=expected_version + 1, updated_at=func.now()))
        if changed.rowcount != 1:
            await self.session.rollback()
            current = await self.session.scalar(select(TourSession.version).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id))
            if current is None: return None
            raise RevisionConflict(int(current))
        revision = TourSessionRevision(id=str(uuid4()), session_id=session_id, version=expected_version + 1,
                                       snapshot_json=_encode(candidate))
        self.session.add(revision)
        proposal.status, proposal.applied_revision_id = "applied", revision.id
        self._add_event(session_id, "proposal_applied", expected_version + 1, {"proposal_id": proposal.id})
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).mark_target_revision_changed(
            session_id, expected_version + 1,
        )
        updated = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id))
        response = await self._session_result(updated, revision)
        self._remember(owner_id, "proposal_apply", idempotency_key, request, response, session_id)
        replay = await self._commit_with_replay(owner_id, "proposal_apply", idempotency_key, request)
        return replay if replay is not None else response

    async def get_session(self, owner_id: str, session_id: str) -> dict | None:
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.deleted_at.is_(None),
        ))
        return await self._session_result(item) if item else None

    async def list_sessions(self, owner_id: str) -> list[dict]:
        items = (await self.session.scalars(select(TourSession).where(
            TourSession.owner_id == owner_id, TourSession.deleted_at.is_(None),
        ).order_by(TourSession.updated_at.desc()))).all()
        return [await self._session_result(item) for item in items]

    async def list_revisions(self, owner_id: str, session_id: str) -> list[dict]:
        if await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        )) is None:
            return []
        rows = (await self.session.scalars(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id,
        ).order_by(TourSessionRevision.version))).all()
        return [{"id": row.id, "version": row.version, "snapshot": _decode(row.snapshot_json),
                 "created_at": row.created_at.isoformat() if row.created_at else None} for row in rows]

    async def add_artifact_reference(
        self, owner_id: str, session_id: str, artifact_type: str, artifact_id: str,
        revision_id: str | None = None,
    ) -> dict | None:
        item = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        if item is None:
            return None
        if revision_id is not None:
            revision = await self.session.scalar(select(TourSessionRevision.id).where(
                TourSessionRevision.id == revision_id,
                TourSessionRevision.session_id == session_id,
            ))
            if revision is None:
                return None
        reference = TourArtifactReference(
            id=str(uuid4()), session_id=session_id, revision_id=revision_id,
            artifact_type=artifact_type, artifact_id=artifact_id,
        )
        self.session.add(reference)
        session_version = await self.session.scalar(select(TourSession.version).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        self._add_event(session_id, "artifact_linked", int(session_version or 1), {
            "artifact_type": artifact_type, "artifact_id": artifact_id,
        })
        await self.session.commit()
        return {"id": reference.id, "session_id": session_id, "revision_id": revision_id,
                "artifact_type": artifact_type, "artifact_id": artifact_id}

    async def list_artifact_references(self, owner_id: str, session_id: str) -> list[dict] | None:
        owned = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        if owned is None:
            return None
        rows = (await self.session.scalars(select(TourArtifactReference).where(
            TourArtifactReference.session_id == session_id,
        ).order_by(TourArtifactReference.created_at))).all()
        return [{"id": row.id, "revision_id": row.revision_id, "artifact_type": row.artifact_type,
                 "artifact_id": row.artifact_id, "created_at": row.created_at.isoformat() if row.created_at else None}
                for row in rows]

    async def restore_revision(
        self, owner_id: str, session_id: str, revision_id: str, expected_version: int,
        idempotency_key: str,
    ) -> dict | None:
        source = await self.session.scalar(select(TourSessionRevision).join(
            TourSession, TourSession.id == TourSessionRevision.session_id,
        ).where(TourSession.owner_id == owner_id, TourSession.id == session_id,
                TourSessionRevision.id == revision_id))
        if source is None:
            return None
        return await self.save_revision(owner_id, session_id, expected_version,
                                        _decode(source.snapshot_json), idempotency_key, "restored")

    async def list_events(self, owner_id: str, session_id: str) -> list[dict] | None:
        owned = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        if owned is None:
            return None
        rows = (await self.session.scalars(select(TourSessionEvent).where(
            TourSessionEvent.session_id == session_id,
        ).order_by(TourSessionEvent.created_at, TourSessionEvent.id))).all()
        return [{"id": row.id, "event_type": row.event_type, "version": row.version,
                 "payload": _decode(row.payload_json),
                 "created_at": row.created_at.isoformat() if row.created_at else None}
                for row in rows]

    async def delete_session(self, owner_id: str, session_id: str, expected_version: int) -> dict | None:
        now = datetime.now(UTC)
        current_revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id,
            TourSessionRevision.version == expected_version,
        ))
        update_result = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.deleted_at.is_(None),
        ).values(version=expected_version + 1, deleted_at=now,
                 deleted_until=now + timedelta(days=TRASH_DAYS), updated_at=now)
                 .execution_options(synchronize_session=False))
        if update_result.rowcount != 1:
            current = await self.session.scalar(select(TourSession.version).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id,
                TourSession.deleted_at.is_(None),
            ))
            await self.session.rollback()
            if current is not None:
                raise RevisionConflict(int(current))
            return None
        if current_revision is not None:
            self.session.add(TourSessionRevision(
                id=str(uuid4()), session_id=session_id, version=expected_version + 1,
                snapshot_json=current_revision.snapshot_json,
            ))
        self._add_event(session_id, "deleted", expected_version + 1)
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).mark_target_revision_changed(
            session_id, expected_version + 1, deleted=True,
        )
        await self.session.commit()
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        return await self._session_result(item)

    async def list_trash(self, owner_id: str) -> list[dict]:
        now = datetime.now(UTC)
        await self.purge_expired_sessions(owner_id)
        items = (await self.session.scalars(select(TourSession).where(
            TourSession.owner_id == owner_id, TourSession.deleted_at.is_not(None),
            TourSession.deleted_until > now,
        ).order_by(TourSession.deleted_at.desc()))).all()
        return [await self._session_result(item) for item in items]

    async def purge_expired_sessions(self, owner_id: str) -> int:
        now = datetime.now(UTC)
        expired_ids = list((await self.session.scalars(select(TourSession.id).where(
            TourSession.owner_id == owner_id,
            TourSession.deleted_until <= now,
        ))).all())
        for session_id in expired_ids:
            from app.repositories.tool_execution import ToolExecutionRepository

            await ToolExecutionRepository(self.session).purge_session(session_id)
            await self.session.execute(delete(TourArtifactReference).where(
                TourArtifactReference.session_id == session_id,
            ))
            await self.session.execute(delete(TourSessionIdempotency).where(
                TourSessionIdempotency.session_id == session_id,
            ))
            await self.session.execute(delete(TourSessionRevision).where(
                TourSessionRevision.session_id == session_id,
            ))
            await self.session.execute(delete(TourSession).where(
                TourSession.id == session_id, TourSession.owner_id == owner_id,
            ))
        await self.session.execute(delete(TourSessionIdempotency).where(
            TourSessionIdempotency.owner_id == owner_id,
            TourSessionIdempotency.expires_at <= now,
        ))
        await self.session.commit()
        return len(expired_ids)

    async def undelete_session(self, owner_id: str, session_id: str) -> dict | None:
        now = datetime.now(UTC)
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.deleted_at.is_not(None), TourSession.deleted_until > now,
        ))
        current_revision = await self.session.scalar(select(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id,
            TourSessionRevision.version == item.version,
        )) if item else None
        update_result = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.deleted_at.is_not(None), TourSession.deleted_until > now,
        ).values(version=TourSession.version + 1, deleted_at=None, deleted_until=None, updated_at=now)
                 .execution_options(synchronize_session=False))
        if update_result.rowcount != 1:
            await self.session.rollback()
            return None
        if current_revision is not None:
            self.session.add(TourSessionRevision(
                id=str(uuid4()), session_id=session_id, version=item.version + 1,
                snapshot_json=current_revision.snapshot_json,
            ))
        self._add_event(session_id, "recovered", item.version + 1)
        await self.session.commit()
        await self.session.refresh(item)
        return await self._session_result(item)

    async def purge_session(self, owner_id: str, session_id: str) -> bool:
        item = await self.session.scalar(select(TourSession.id).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.deleted_at.is_not(None),
        ))
        if item is None:
            return False
        from app.repositories.tool_execution import ToolExecutionRepository

        await ToolExecutionRepository(self.session).purge_session(session_id)
        await self.session.execute(delete(TourArtifactReference).where(
            TourArtifactReference.session_id == session_id,
        ))
        await self.session.execute(delete(TourSessionIdempotency).where(
            TourSessionIdempotency.session_id == session_id,
        ))
        await self.session.execute(delete(TourSessionRevision).where(
            TourSessionRevision.session_id == session_id,
        ))
        await self.session.execute(delete(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        await self.session.commit()
        return True

    async def cleanup_expired_idempotency(self) -> int:
        result = await self.session.execute(delete(TourSessionIdempotency).where(
            TourSessionIdempotency.expires_at <= datetime.now(UTC),
        ))
        await self.session.commit()
        return int(result.rowcount or 0)
