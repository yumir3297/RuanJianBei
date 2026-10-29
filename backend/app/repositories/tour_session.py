from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tour_session import (
    TourArtifactReference,
    TourSession,
    TourSessionIdempotency,
    TourSessionRevision,
)

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
        await self.session.flush()
        result = await self._session_result(item, revision)
        self._remember(owner_id, "create", idempotency_key, request, result, item.id)
        replay = await self._commit_with_replay(owner_id, "create", idempotency_key, request)
        if replay is not None:
            return replay
        return result

    async def save_revision(
        self, owner_id: str, session_id: str, expected_version: int, payload: dict,
        idempotency_key: str,
    ) -> dict:
        request = {"session_id": session_id, "expected_version": expected_version, "snapshot": payload}
        replay = await self._replay(owner_id, "save", idempotency_key, request)
        if replay is not None:
            return replay
        result = await self.session.execute(update(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
            TourSession.version == expected_version, TourSession.deleted_at.is_(None),
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
        item = await self.session.scalar(select(TourSession).where(
            TourSession.id == session_id, TourSession.owner_id == owner_id,
        ))
        result_payload = await self._session_result(item, revision)
        self._remember(owner_id, "save", idempotency_key, request, result_payload, session_id)
        replay = await self._commit_with_replay(owner_id, "save", idempotency_key, request)
        if replay is not None:
            return replay
        return result_payload

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
                                        _decode(source.snapshot_json), idempotency_key)

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
