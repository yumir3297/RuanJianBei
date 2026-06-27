from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.visitor import VisitorProfile


class VisitorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_session(self, session_id: str) -> VisitorProfile | None:
        stmt = select(VisitorProfile).where(VisitorProfile.session_id == session_id)
        return self.session.scalar(stmt)

    def upsert(self, session_id: str, interests: list[str], audience_type: str) -> VisitorProfile:
        profile = self.get_by_session(session_id)
        if profile is None:
            profile = VisitorProfile(
                session_id=session_id,
                preference_tags=json.dumps(interests, ensure_ascii=False),
                audience_type=audience_type,
            )
        else:
            profile.preference_tags = json.dumps(interests, ensure_ascii=False)
            profile.audience_type = audience_type
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def count(self) -> int:
        return self.session.scalar(select(func.count(VisitorProfile.id))) or 0

