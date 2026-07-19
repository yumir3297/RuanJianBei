from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog
from app.models.visitor_feedback import VisitorFeedback
from app.schemas.experience import ExperienceReport, ExperienceSuggestion, ExperienceTopicItem, ExperienceTrendItem

RANGE_DAYS = {"today": 1, "week": 7, "month": 30}
REASON_LABELS = {"accuracy": "回答不准确", "detail": "内容不够详细", "recommendation": "推荐不符合需求", "latency": "回复等待较久", "other": "其他建议"}


class ExperienceReportService:
    """Aggregates persisted visitor interactions for the administration report."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build(self, range_key: str) -> ExperienceReport:
        days = RANGE_DAYS.get(range_key, 7)
        start = datetime.now() - timedelta(days=days - 1)
        logs_result = await self.session.execute(
            select(ChatLog).where(ChatLog.created_at >= start).order_by(ChatLog.created_at)
        )
        logs = logs_result.scalars().all()
        real_result = await self.session.execute(
            select(VisitorFeedback)
            .where(VisitorFeedback.created_at >= start, VisitorFeedback.is_demo.is_(False))
            .order_by(VisitorFeedback.created_at)
        )
        real = real_result.scalars().all()
        if real:
            feedback, data_mode = real, "real"
        else:
            demo_result = await self.session.execute(
                select(VisitorFeedback)
                .where(VisitorFeedback.created_at >= start, VisitorFeedback.is_demo.is_(True))
                .order_by(VisitorFeedback.created_at)
            )
            demo = demo_result.scalars().all()
            feedback, data_mode = demo, "demo" if demo else "empty"

        positive, negative = sum(x.rating == "positive" for x in feedback), sum(x.rating == "negative" for x in feedback)
        total = len(feedback)
        satisfaction = round(positive / total * 100, 1) if total else None
        interactions, sessions = len(logs), len({x.session_id for x in logs})
        if not interactions and data_mode == "demo":
            interactions, sessions = total, len({x.session_id for x in feedback})
        buckets = defaultdict(lambda: {"positive": 0, "negative": 0})
        for item in feedback:
            buckets[item.created_at.strftime("%m-%d")][item.rating] += 1
        trend = []
        for offset in range(days):
            day = (start + timedelta(days=offset)).strftime("%m-%d")
            counts = buckets[day]
            count = counts["positive"] + counts["negative"]
            trend.append(ExperienceTrendItem(date=day, positive=counts["positive"], negative=counts["negative"], satisfaction_rate=round(counts["positive"] / count * 100, 1) if count else None))
        questions = Counter(x.normalized_query for x in logs if x.normalized_query.strip())
        reasons = Counter(REASON_LABELS.get(x.reason_code or "other", "其他建议") for x in feedback if x.rating == "negative")
        suggestions = self._suggest(questions, reasons, satisfaction)
        return ExperienceReport(
            range=range_key if range_key in RANGE_DAYS else "week", data_mode=data_mode, generated_at=datetime.now(), service_sessions=sessions,
            interaction_count=interactions, feedback_count=total, feedback_coverage=round(total / interactions * 100, 1) if interactions else 0,
            satisfaction_rate=satisfaction, positive_count=positive, negative_count=negative,
            sentiment_summary=(f"已收集 {total} 条{'真实' if data_mode == 'real' else '评委演示'}反馈，好评 {positive} 条、待改进 {negative} 条。" if total else "暂未收集游客主动评价；满意度将在收到真实反馈后自动计算。"),
            trend=trend, hot_questions=[ExperienceTopicItem(label=k, count=v) for k, v in questions.most_common(8)],
            negative_reasons=[ExperienceTopicItem(label=k, count=v) for k, v in reasons.most_common(5)], suggestions=suggestions,
        )

    @staticmethod
    def _suggest(questions, reasons, satisfaction):
        result = []
        if satisfaction is not None and satisfaction < 80:
            result.append(ExperienceSuggestion(level="attention", title="优先处理负向体验", detail="当前有效反馈满意度低于 80%，建议先复盘负反馈原因与对应回答。"))
        if reasons:
            label, count = reasons.most_common(1)[0]
            result.append(ExperienceSuggestion(level="optimize", title=f"优化\u201c{label}\u201d", detail=f"该问题出现 {count} 次，可在知识库或回答模板中优先补强。"))
        if questions:
            label, count = questions.most_common(1)[0]
            result.append(ExperienceSuggestion(level="keep", title="完善热门问答", detail=f"\u201c{label}\u201d在当前周期被问及 {count} 次，建议作为快捷入口或重点讲解内容。"))
        return result[:3] or [ExperienceSuggestion(level="keep", title="开始积累真实反馈", detail="游客完成问答后可点击有帮助或需要改进，系统将自动更新满意度趋势。")]
