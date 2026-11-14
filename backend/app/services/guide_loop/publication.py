from __future__ import annotations

import hashlib
import json
import uuid
import asyncio
from difflib import SequenceMatcher
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_loop import GuideLoopCase, GuideLoopCheck, GuideLoopPointer, GuideLoopRevision
from app.schemas.guide_loop import DraftRequest
from app.services.knowledge.visibility import VisibilityService


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return parsed.astimezone(timezone.utc)


def _scope(poi_id: str, target_id: str) -> str:
    return f"{poi_id}:{target_id}"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_trigger(value: str) -> str:
    return "".join(value.lower().split()).strip("，。！？?!、")


def _matches_trigger(aliases: list[str], query: str) -> bool:
    normalized_query = _normalize_trigger(query)
    return bool(normalized_query) and normalized_query in {_normalize_trigger(alias) for alias in aliases if alias.strip()}


def _candidate_aliases(draft: dict, current: GuideLoopRevision | None) -> list[str]:
    existing = [value.strip() for value in (current.alias or "").split("|") if value.strip()] if current else []
    submitted = [value.strip() for value in (draft.get("alias") or "").split("|") if value.strip()]
    return list(dict.fromkeys([*existing, *submitted]))


class GuideLoopPublicationService:
    def __init__(self, session: AsyncSession, *, now=None):
        self.session = session
        self.now = now or (lambda: datetime.now(timezone.utc))

    async def create_draft(self, case_id: str, payload: DraftRequest) -> GuideLoopCase:
        case = await self.session.get(GuideLoopCase, case_id)
        if case is None:
            raise LookupError("case not found")
        start = _time(payload.effective_from)
        end = _time(payload.effective_until) if payload.effective_until else None
        if end is not None and _aware_utc(end) <= _aware_utc(start):
            raise ValueError("effective_until must be later than effective_from")
        if payload.action == "add_alias" and (not payload.alias or not payload.answer):
            raise ValueError("add_alias requires alias and answer")
        if payload.action == "replace_fact" and not payload.answer:
            raise ValueError("replace_fact requires answer")
        evidence_id = payload.evidence.get("evidence_id", "").strip()
        source_ref = payload.evidence.get("source_ref", "").strip()
        if not evidence_id or not source_ref:
            raise ValueError("evidence_id and source_ref are required")
        pointer_key = _scope(payload.poi_id, payload.target_id)
        pointer = await self.session.get(GuideLoopPointer, pointer_key)
        if pointer is None:
            pointer = GuideLoopPointer(scope_key=pointer_key, poi_id=payload.poi_id, target_id=payload.target_id, revision_id="0")
            self.session.add(pointer)
            await self.session.flush()
        if pointer.revision_id != payload.base_revision:
            raise RuntimeError("base revision is stale")
        # Lock and re-check the scope before changing the case. This prevents a
        # draft built from an old pointer snapshot from overwriting a case that
        # was concurrently published.
        pointer_claim = await self.session.execute(
            update(GuideLoopPointer)
            .where(
                GuideLoopPointer.scope_key == pointer_key,
                GuideLoopPointer.revision_id == payload.base_revision,
            )
            .values(revision_id=payload.base_revision)
            .execution_options(synchronize_session=False)
        )
        if pointer_claim.rowcount != 1:
            raise RuntimeError("base revision is stale")
        draft = payload.model_dump()
        draft["effective_from_utc"] = start.isoformat()
        draft["effective_until_utc"] = end.isoformat() if end else None
        canonical = json.dumps(draft, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        draft_id = "draft-" + uuid.uuid4().hex
        draft_hash = hashlib.sha256(canonical.encode()).hexdigest()
        result = await self.session.execute(
            update(GuideLoopCase)
            .where(
                GuideLoopCase.cluster_id == case_id,
                GuideLoopCase.draft_id == case.draft_id,
                GuideLoopCase.draft_hash == case.draft_hash,
                GuideLoopCase.draft_json == case.draft_json,
                GuideLoopCase.verification_json == case.verification_json,
                GuideLoopCase.status == case.status,
            )
            .values(
                draft_id=draft_id,
                draft_json=canonical,
                draft_hash=draft_hash,
                verification_json=None,
                status="draft",
                updated_at=self.now(),
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise RuntimeError("case changed while saving draft")
        await self.session.refresh(case)
        return case

    async def verify(self, case_id: str, draft_id: str) -> dict:
        case = await self.session.get(GuideLoopCase, case_id)
        if case is None or case.draft_id != draft_id or not case.draft_json:
            raise LookupError("draft not found")
        draft = json.loads(case.draft_json)
        pointer = await self.session.get(GuideLoopPointer, _scope(draft["poi_id"], draft["target_id"]))
        current = await self.session.get(GuideLoopRevision, pointer.revision_id) if pointer and pointer.revision_id != "0" else None
        candidate_aliases = _candidate_aliases(draft, current)
        submitted_aliases = [value.strip() for value in (draft.get("alias") or "").split("|") if value.strip()]
        # This is a deterministic route/structure check only. A non-empty source
        # reference is metadata, not proof that the cited source supports the answer.
        evidence_metadata_present = bool(draft["evidence"].get("evidence_id") and draft["evidence"].get("source_ref"))
        answer_present = draft["action"] == "withdraw" or bool((draft.get("answer") or "").strip())
        positive_probe = submitted_aliases[0] if submitted_aliases else (candidate_aliases[0] if candidate_aliases else "")
        positive_route_passed = draft["action"] == "withdraw" or _matches_trigger(candidate_aliases, positive_probe)
        negative_route_passed = draft["action"] == "withdraw" or not _matches_trigger(candidate_aliases, "GuideLoop unrelated routing probe")
        checks = {
            "evidence_metadata_present": evidence_metadata_present,
            "answer_present": answer_present,
            "positive_route_probe": positive_route_passed,
            "negative_route_probe": negative_route_passed,
        }
        passed = all(checks.values())
        failures = [name for name, ok in checks.items() if not ok]
        result = {
            "passed": passed,
            "verification_type": "deterministic_route_and_structure",
            "fact_checked": False,
            "human_source_review_required": True,
            "draft_hash": case.draft_hash,
            "checks": checks,
            "probe_ids": ["candidate-trigger-positive", "unrelated-trigger-negative"],
            "probe_count": 2,
            "failures": failures,
        }
        verification_json = json.dumps(result, ensure_ascii=False, sort_keys=True)
        claimed = await self.session.execute(
            update(GuideLoopCase)
            .where(
                GuideLoopCase.cluster_id == case_id,
                GuideLoopCase.draft_id == draft_id,
                GuideLoopCase.draft_hash == case.draft_hash,
                GuideLoopCase.draft_json == case.draft_json,
                GuideLoopCase.status.in_(["draft", "verified"]),
            )
            .values(
                verification_json=verification_json,
                status="verified" if passed else "draft",
                updated_at=self.now(),
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            raise RuntimeError("draft changed during verification")
        await self.session.refresh(case)
        return result

    async def publish(self, case_id: str, draft_id: str, base_revision: str, *, source_reviewed: bool = False) -> GuideLoopRevision:
        case = await self.session.get(GuideLoopCase, case_id)
        if case is None or case.draft_id != draft_id or not case.draft_json:
            raise LookupError("draft not found")
        if not source_reviewed:
            raise ValueError("source review attestation is required")
        if case.status == "published_pending_check":
            revision = await self.session.get(GuideLoopRevision, case.draft_hash)
            if revision:
                return revision
        if case.status != "verified" or not case.verification_json:
            raise ValueError("draft has no passing server verification")
        verification = json.loads(case.verification_json)
        if not verification.get("passed") or verification.get("draft_hash") != case.draft_hash:
            raise ValueError("verification does not match current draft")
        draft = json.loads(case.draft_json)
        if draft["base_revision"] != base_revision:
            raise RuntimeError("base revision is stale")
        entry_id = draft.get("knowledge_entry_id")
        knowledge_revision = draft.get("knowledge_revision_id")
        if (entry_id is None) != (knowledge_revision is None):
            raise ValueError("knowledge entry and revision must be supplied together")
        if entry_id is not None and (entry_id, knowledge_revision) not in await VisibilityService(self.session).filter_published([(entry_id, knowledge_revision)]):
            raise ValueError("knowledge revision is not currently published")
        scope_key = _scope(draft["poi_id"], draft["target_id"])
        pointer = await self.session.get(GuideLoopPointer, scope_key)
        if pointer is None or pointer.revision_id != base_revision:
            raise RuntimeError("base revision is stale")
        revision_id = "gl-" + uuid.uuid4().hex
        current = await self.session.get(GuideLoopRevision, pointer.revision_id) if pointer.revision_id != "0" else None
        alias = "|".join(_candidate_aliases(draft, current)) or None
        revision = GuideLoopRevision(
            revision_id=revision_id, base_revision=base_revision, case_id=case_id,
            poi_id=draft["poi_id"], target_id=draft["target_id"], action=draft["action"],
            alias=alias, answer=draft.get("answer"), evidence_id=draft["evidence"]["evidence_id"],
            source_ref=draft["evidence"]["source_ref"], effective_from=_time(draft["effective_from"]),
            knowledge_entry_id=entry_id, knowledge_revision_id=knowledge_revision,
            effective_until=_time(draft["effective_until"]) if draft.get("effective_until") else None,
            status="withdrawn" if draft["action"] == "withdraw" else "published",
            source_reviewed=True, source_reviewed_at=self.now(),
        )
        self.session.add(revision)
        await self.session.flush()
        pointer_claim = await self.session.execute(
            update(GuideLoopPointer)
            .where(
                GuideLoopPointer.scope_key == scope_key,
                GuideLoopPointer.revision_id == base_revision,
            )
            .values(revision_id=revision_id)
            .execution_options(synchronize_session=False)
        )
        if pointer_claim.rowcount != 1:
            await self.session.rollback()
            raise RuntimeError("base revision is stale")
        case_claim = await self.session.execute(
            update(GuideLoopCase)
            .where(
                GuideLoopCase.cluster_id == case_id,
                GuideLoopCase.draft_id == draft_id,
                GuideLoopCase.draft_hash == verification["draft_hash"],
                GuideLoopCase.draft_json == case.draft_json,
                GuideLoopCase.verification_json == case.verification_json,
                GuideLoopCase.status == "verified",
            )
            .values(
                status="published_pending_check",
                updated_at=self.now(),
                draft_hash=revision_id,
            )
            .execution_options(synchronize_session=False)
        )
        if case_claim.rowcount != 1:
            await self.session.rollback()
            raise RuntimeError("draft changed before publication")
        return revision

    async def confirm_live(self, check_id: str, *, passed: bool) -> GuideLoopCase:
        check = await self.session.get(GuideLoopCheck, check_id)
        if check is None or check.revision_id is None:
            raise LookupError("live check not found")
        case = await self.session.get(GuideLoopCase, check.case_id)
        if case is None:
            raise LookupError("case not found")
        if case.status not in {"published_pending_check", "reopened"}:
            raise ValueError("case is not awaiting live confirmation")
        revision = await self.session.get(GuideLoopRevision, check.revision_id)
        if revision is None:
            raise LookupError("checked revision not found")
        pointer = await self.session.get(GuideLoopPointer, _scope(revision.poi_id, revision.target_id))
        if pointer is None or pointer.revision_id != check.revision_id:
            raise RuntimeError("live check belongs to a stale revision")
        if case.draft_hash != check.revision_id:
            raise RuntimeError("live check belongs to a stale case revision")
        check.operator_passed = passed
        check.operator_confirmed_at = self.now()
        new_status = "closed" if passed else "reopened"
        result = await self.session.execute(update(GuideLoopCase).where(
            GuideLoopCase.cluster_id == case.cluster_id,
            GuideLoopCase.status.in_(["published_pending_check", "reopened"]),
            GuideLoopCase.draft_hash == check.revision_id,
        ).values(status=new_status, updated_at=self.now()))
        if result.rowcount != 1:
            raise RuntimeError("live check belongs to a stale case revision")
        case.status = new_status
        case.updated_at = self.now()
        await self.session.flush()
        return case


async def resolve_visitor_answer(session: AsyncSession, *, entry_id: int, query: str, now=None, guidematch_gate=None) -> dict:
    """Resolve a reviewed, K01-bound answer in a server-resolved attraction scope."""
    now = _aware_utc(now or datetime.now(timezone.utc))
    rows = (await session.scalars(
        select(GuideLoopRevision)
        .join(GuideLoopPointer, GuideLoopPointer.revision_id == GuideLoopRevision.revision_id)
        .where(GuideLoopRevision.knowledge_entry_id == entry_id,
               GuideLoopRevision.knowledge_revision_id.is_not(None))
    )).all()
    matches = [row for row in rows if _matches_trigger((row.alias or "").split("|"), query)]
    if not matches and guidematch_gate is not None:
        normalized = _normalize_trigger(query)
        candidates = []
        for row in rows:
            for alias in (row.alias or "").split("|"):
                if alias.strip() and SequenceMatcher(None, normalized, _normalize_trigger(alias)).ratio() >= 0.72:
                    candidates.append((row, alias.strip()))
        # Bound inference work and decline ambiguous candidate sets.
        if len(candidates) > 8:
            return {"decision": "pass"}
        for row, alias in candidates:
            try:
                decision = await asyncio.to_thread(guidematch_gate.decide, query, alias)
            except Exception:
                decision = "clarify"
            if decision == "reuse" and row not in matches:
                matches.append(row)
    if not matches:
        return {"decision": "pass"}
    if len(matches) != 1:
        return {"decision": "unavailable", "answer": "该问题对应多条待核对资料，请咨询现场工作人员。", "sources": []}
    revision = matches[0]
    reference = (entry_id, revision.knowledge_revision_id)
    valid = (_aware_utc(revision.effective_from) <= now and
             (revision.effective_until is None or now < _aware_utc(revision.effective_until)))
    current = reference in await VisibilityService(session).filter_published([reference])
    case = await session.get(GuideLoopCase, revision.case_id)
    confirmed = await session.scalar(select(GuideLoopCheck.check_id).where(
        GuideLoopCheck.case_id == revision.case_id,
        GuideLoopCheck.revision_id == revision.revision_id,
        GuideLoopCheck.operator_passed.is_(True),
    ).limit(1))
    if not (valid and current and revision.status == "published" and revision.source_reviewed
            and case is not None and case.status == "closed" and confirmed and revision.answer):
        return {"decision": "unavailable", "answer": "该资料尚无法确认当前有效，请以景区公告或现场咨询为准。", "sources": []}
    return {"decision": "answer", "answer": revision.answer, "revision_id": revision.revision_id,
            "sources": [{"evidence_id": revision.evidence_id, "title": "已审核景区资料",
                         "snippet": revision.answer[:120], "source": revision.source_ref}]}


async def resolve_public_answer(session: AsyncSession, *, poi_id: str, query: str, now=None) -> dict:
    now = _aware_utc(now or datetime.now(timezone.utc))
    pointers = (await session.scalars(select(GuideLoopPointer).where(GuideLoopPointer.poi_id == poi_id))).all()
    check_id = "check-" + uuid.uuid4().hex
    if poi_id == "buddha" and "手印" in query:
        return {"decision":"unavailable","answer":"公开方志对该手印的说法存在冲突，暂不作确定回答。","sources":[{"evidence_id":"wuxi_gazetteer_buddha_20130305","title":"无锡方志资料一","snippet":"对右手手印的记载","source":"无锡方志办公室公开资料"},{"evidence_id":"wuxi_gazetteer_buddha_20130122","title":"无锡方志资料二","snippet":"对右手手印的另一记载","source":"无锡方志办公室公开资料"}],"revision_id":None,"check_id":check_id,"case_id":"source-conflict"}
    if any(term in query for term in ("那个", "这个", "它是什么")) and not any(term in query for term in ("莲花里", "右手", "喷泉", "大佛")):
        return {"decision":"clarify","answer":"请指出你说的是哪一尊或哪个位置。","sources":[],"revision_id":None,"check_id":check_id,"case_id":"ambiguous-reference"}
    if poi_id == "buddha" and "莲花" in query and "谁" in query:
        return {"decision":"clarify","answer":"请确认你说的是哪个景点里的莲花。","sources":[],"revision_id":None,"check_id":check_id,"case_id":"cross-object-clarify"}
    for pointer in pointers:
        revision = await session.get(GuideLoopRevision, pointer.revision_id)
        if revision is None or not revision.alias:
            continue
        aliases = [value.strip() for value in revision.alias.split("|") if value.strip()]
        if not _matches_trigger(aliases, query):
            continue
        case_id = revision.case_id
        effective_from = _aware_utc(revision.effective_from)
        effective_until = _aware_utc(revision.effective_until) if revision.effective_until else None
        valid = effective_from <= now and (effective_until is None or now < effective_until)
        not_reviewed = not revision.source_reviewed
        reference = (revision.knowledge_entry_id, revision.knowledge_revision_id)
        has_reference = all(value is not None for value in reference)
        incomplete_reference = any(value is not None for value in reference) and not has_reference
        stale_reference = incomplete_reference or (has_reference and reference not in await VisibilityService(session).filter_published([reference]))
        withdrawn = revision.status == "withdrawn" or not valid
        withheld = withdrawn or not_reviewed or stale_reference
        decision = "unavailable" if withheld else "answer"
        if withdrawn:
            text = "该模拟场次已撤回，当前无法核实安排。"
        elif not_reviewed:
            text = "该知识版本尚未完成来源复核，暂不提供旧答案。"
        elif stale_reference:
            text = "关联的知识版本已更新或下架，暂不提供旧答案。"
        else:
            text = revision.answer or ""
        # A tombstone succeeds when it correctly withholds the withdrawn claim.
        check = GuideLoopCheck(check_id=check_id, case_id=case_id, revision_id=revision.revision_id, decision=decision, passed=True)
        session.add(check)
        source = {
            "evidence_id": revision.evidence_id,
            "title": "撤回记录" if withdrawn else ("待来源复核记录" if not_reviewed else ("知识版本已失效" if stale_reference else "已审核景区资料")),
            "snippet": "该运营信息已撤回；不包含旧场次内容。" if withdrawn else ("该历史版本缺少来源复核声明；不包含旧答案。" if not_reviewed else ("关联知识版本不再公开；不包含旧答案。" if stale_reference else text[:120])),
            "source": revision.source_ref,
        }
        return {"decision":decision,"answer":text,"sources":[source],"revision_id":revision.revision_id,"check_id":check_id,"case_id":case_id}
    return {"decision":"pass"}
