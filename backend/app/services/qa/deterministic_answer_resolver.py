from __future__ import annotations

from dataclasses import dataclass, field

from app.services.qa.answer_fast_paths import (
    resolve_ticket_answer,
    resolve_unverified_schedule_answer,
)


@dataclass(slots=True)
class DeterministicAnswerDecision:
    answer: str
    hit_level: str
    sources: list[dict] = field(default_factory=list)
    status_text: str | None = None


class DeterministicAnswerResolver:
    """Resolve policy-first schedule, ticket, and static-route answers."""

    def __init__(self, *, route_builder) -> None:
        self.route_builder = route_builder

    async def resolve(self, request, *, vision_present: bool, intent: str) -> DeterministicAnswerDecision | None:
        schedule_answer = resolve_unverified_schedule_answer(request.query)
        if schedule_answer is not None:
            return DeterministicAnswerDecision(
                answer=schedule_answer,
                hit_level="schedule_unverified",
            )

        ticket_answer = resolve_ticket_answer(request.query)
        if ticket_answer is not None:
            return DeterministicAnswerDecision(
                answer=ticket_answer,
                hit_level="ticket_unverified",
            )

        if vision_present or intent != "static_route":
            return None
        route = await self.route_builder.build_answer(request)
        if route is None:
            return None

        answer, sources = route
        return DeterministicAnswerDecision(
            answer=answer,
            sources=sources,
            hit_level="static_route" if sources else "route_clarification",
            status_text="正在整理游览路线...",
        )
