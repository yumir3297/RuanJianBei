from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.route import RouteTemplate


class RouteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[RouteTemplate]:
        stmt = select(RouteTemplate).order_by(RouteTemplate.id.asc())
        return list(self.session.scalars(stmt))

    def get(self, route_id: str) -> RouteTemplate | None:
        return self.session.get(RouteTemplate, route_id)

    def replace_all(self, routes: list[RouteTemplate]) -> int:
        self.session.execute(delete(RouteTemplate))
        self.session.add_all(routes)
        self.session.flush()
        return len(routes)

    def count(self) -> int:
        return self.session.scalar(select(func.count(RouteTemplate.id))) or 0
