from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat_log import ChatLog


class ChatLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        session_id: str,
        raw_query: str,
        normalized_query: str,
        answer: str,
        sources: list[dict],
        hit_level: str,
        latency_ms: int,
    ) -> ChatLog:
        log = ChatLog(
            session_id=session_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            answer=answer,
            sources=json.dumps(sources, ensure_ascii=False),
            hit_level=hit_level,
            latency_ms=latency_ms,
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def count(self) -> int:
        return self.session.scalar(select(func.count(ChatLog.id))) or 0

