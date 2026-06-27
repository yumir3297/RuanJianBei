from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.behavior_summary import BehaviorSummary


class BehaviorSummaryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_all(self, summaries: list[BehaviorSummary]) -> int:
        self.session.execute(delete(BehaviorSummary))
        self.session.add_all(summaries)
        self.session.flush()
        return len(summaries)

    def get_latest(self) -> BehaviorSummary | None:
        stmt = select(BehaviorSummary).order_by(BehaviorSummary.updated_at.desc(), BehaviorSummary.id.desc())
        return self.session.scalar(stmt)

    def count(self) -> int:
        return self.session.scalar(select(func.count(BehaviorSummary.id))) or 0
