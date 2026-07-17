from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.api.auth import require_admin_token
from app.models.chat_log import ChatLog
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.models.visitor import VisitorProfile
from app.models.visitor_feedback import VisitorFeedback
from app.schemas.experience import FeedbackCreate, FeedbackResponse, ExperienceReport
from app.schemas.insights import BlindSpotTopItem, QATrend, SpotAttentionItem, VisitorGroups
from app.services.experience_report import ExperienceReportService


router = APIRouter()

HIT_LEVEL_LABELS = {
    "faq_exact": "FAQ 精确匹配",
    "faq_fuzzy": "FAQ 模糊匹配",
    "faq_semantic": "FAQ 语义匹配",
    "cache": "缓存命中",
    "rag": "RAG 检索回答",
    "rag_insufficient": "RAG 证据不足",
    "rag_llm_fallback": "RAG 大模型补全",
    "blind": "知识盲区",
}


def _load_json_list(payload: str | list[Any] | None) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not payload:
        return []
    try:
        items = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return []
    return items if isinstance(items, list) else []


def _source_titles(payload: str | list[Any] | None) -> list[str]:
    titles: list[str] = []
    for item in _load_json_list(payload):
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or item.get("source")
            if title:
                titles.append(str(title).strip())
            continue
        text = str(item).strip()
        if text:
            titles.append(text)
    return titles


def _tags(payload: str | list[Any] | None) -> list[str]:
    return [text for text in (str(item).strip() for item in _load_json_list(payload)) if text]


def _hit_level_label(level: str | None) -> str:
    if not level:
        return "未分类"
    if level in HIT_LEVEL_LABELS:
        return HIT_LEVEL_LABELS[level]
    if level.startswith("faq_"):
        return f"FAQ {level.removeprefix('faq_').replace('_', ' ')}"
    if level.startswith("rag_"):
        return f"RAG {level.removeprefix('rag_').replace('_', ' ')}"
    return level


@router.get("/spot-attention", response_model=list[SpotAttentionItem])
def get_spot_attention(_: None = Depends(require_admin_token), db: Session = Depends(get_db_session)) -> list[SpotAttentionItem]:
    logs = db.execute(select(ChatLog.sources)).scalars().all()

    spot_counts: Counter[str] = Counter()
    for sources in logs:
        for title in _source_titles(sources):
            spot_counts[title] += 1

    total = sum(spot_counts.values()) or 1
    return [
        SpotAttentionItem(name=name, count=count, ratio=round(count / total, 2))
        for name, count in spot_counts.most_common(10)
    ]


@router.get("/visitor-groups", response_model=VisitorGroups)
def get_visitor_groups(_: None = Depends(require_admin_token), db: Session = Depends(get_db_session)) -> VisitorGroups:
    profiles = db.execute(
        select(VisitorProfile.audience_type, VisitorProfile.preference_tags)
    ).all()

    audience_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()

    for audience_type, preference_tags in profiles:
        if audience_type:
            audience_counts[audience_type] += 1
        for tag in _tags(preference_tags):
            tag_counts[tag] += 1

    total_audience = sum(audience_counts.values()) or 1

    return VisitorGroups(
        audience_distribution=[
            {
                "group_label": label,
                "count": count,
                "ratio": round(count / total_audience, 2),
            }
            for label, count in audience_counts.most_common()
        ],
        top_tags=[
            {"tag": tag, "count": count}
            for tag, count in tag_counts.most_common(10)
        ],
    )


@router.get("/qa-trend", response_model=QATrend)
def get_qa_trend(_: None = Depends(require_admin_token), db: Session = Depends(get_db_session)) -> QATrend:
    thirty_days_ago = datetime.now() - timedelta(days=30)

    daily = db.execute(
        select(
            func.date(ChatLog.created_at).label("date"),
            func.count().label("count"),
        )
        .where(ChatLog.created_at >= thirty_days_ago)
        .group_by(func.date(ChatLog.created_at))
        .order_by(func.date(ChatLog.created_at))
    ).all()

    hit_levels = db.execute(
        select(ChatLog.hit_level, func.count().label("count"))
        .group_by(ChatLog.hit_level)
    ).all()

    total_hits = sum(count for _, count in hit_levels) or 1

    return QATrend(
        daily_trend=[
            {"date": str(date), "count": count}
            for date, count in daily
        ],
        hit_distribution=[
            {
                "level": level or "unknown",
                "label": _hit_level_label(level),
                "count": count,
                "ratio": round(count / total_hits, 2),
            }
            for level, count in hit_levels
        ],
    )


@router.get("/blind-spot-top", response_model=list[BlindSpotTopItem])
def get_blind_spot_top(_: None = Depends(require_admin_token), db: Session = Depends(get_db_session)) -> list[BlindSpotTopItem]:
    spots = db.execute(
        select(KnowledgeBlindSpot.normalized_query, KnowledgeBlindSpot.hit_count)
        .where(KnowledgeBlindSpot.status == "open")
        .order_by(KnowledgeBlindSpot.hit_count.desc())
        .limit(10)
    ).all()

    return [
        BlindSpotTopItem(rank=index + 1, query=query, hit_count=hit_count)
        for index, (query, hit_count) in enumerate(spots)
    ]


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db_session)) -> FeedbackResponse:
    if payload.chat_log_id is not None:
        log = db.get(ChatLog, payload.chat_log_id)
        if log is None or log.session_id != payload.session_id:
            raise HTTPException(status_code=404, detail="未找到可评价的问答记录")
        existing = db.execute(select(VisitorFeedback).where(VisitorFeedback.chat_log_id == payload.chat_log_id, VisitorFeedback.is_demo.is_(False))).scalar_one_or_none()
        if existing is not None:
            existing.rating = payload.rating
            existing.reason_code = payload.reason_code
            existing.comment = payload.comment
            db.commit()
            return FeedbackResponse(id=existing.id, rating=existing.rating, message="评价已更新")
    feedback = VisitorFeedback(**payload.model_dump(), is_demo=False)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(id=feedback.id, rating=feedback.rating, message="感谢您的反馈")


@router.get("/experience-report", response_model=ExperienceReport)
def get_experience_report(
    range: str = Query(default="week", pattern="^(today|week|month)$"),
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db_session),
) -> ExperienceReport:
    return ExperienceReportService(db).build(range)
