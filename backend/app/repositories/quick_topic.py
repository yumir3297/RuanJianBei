from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quick_topic import QuickTopic


class QuickTopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_enabled(self) -> list[QuickTopic]:
        stmt = (
            select(QuickTopic)
            .where(QuickTopic.is_enabled.is_(True))
            .order_by(QuickTopic.sort_order.asc(), QuickTopic.key.asc())
        )
        return list(self.session.scalars(stmt))

    def get_enabled(self, topic_key: str) -> QuickTopic | None:
        stmt = select(QuickTopic).where(
            QuickTopic.key == topic_key,
            QuickTopic.is_enabled.is_(True),
        )
        return self.session.scalar(stmt)

    def seed_missing(self, topics: Iterable[dict]) -> int:
        existing_keys = set(self.session.scalars(select(QuickTopic.key)))
        missing = [QuickTopic(**topic) for topic in topics if topic["key"] not in existing_keys]
        if not missing:
            return 0

        self.session.add_all(missing)
        self.session.commit()
        return len(missing)
