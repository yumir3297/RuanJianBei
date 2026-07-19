from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor import VisitorProfile


class VisitorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_session(self, session_id: str) -> VisitorProfile | None:
        stmt = select(VisitorProfile).where(VisitorProfile.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, session_id: str, interests: list[str], audience_type: str) -> VisitorProfile:
        profile = await self.get_by_session(session_id)
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
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(VisitorProfile.id)))
        return result.scalar_one_or_none() or 0
