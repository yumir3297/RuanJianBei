from app.schemas.selection import SelectionContext
from app.services.qa.followup_suggestions import FollowUpSuggestionService
from app.services.qa.guided_selector import ResolvedInteraction
from app.services.rag.base import RetrievalScope


def resolved_interaction(
    *,
    mode: str,
    subject: str | None,
    topic_key: str | None = None,
) -> ResolvedInteraction:
    return ResolvedInteraction(
        selection=SelectionContext(mode=mode, attraction_id=13 if mode == "attraction" else None, topic_key=topic_key),
        scope=RetrievalScope(source_entry_id=13) if mode == "attraction" else None,
        resolution_source="selection" if mode != "free_chat" else "default",
        active_subject=subject,
    )


def test_attraction_followups_use_validated_subject_and_topic_template() -> None:
    items = FollowUpSuggestionService().generate(
        resolved_interaction(mode="attraction", subject="灵山大佛", topic_key="history")
    )

    assert len(items) == 4
    assert items[0] == {
        "label": "继续了解历史",
        "query": "灵山大佛有什么历史文化背景？",
    }
    assert all("灵山大佛" in item["query"] for item in items)


def test_route_and_free_chat_followups_stay_within_controlled_limit() -> None:
    service = FollowUpSuggestionService()
    route_items = service.generate(resolved_interaction(mode="route", subject="经典一日游"))
    free_items = service.generate(resolved_interaction(mode="free_chat", subject=None))

    assert len(route_items) == 4
    assert len(free_items) == 3
    assert len({item["query"] for item in route_items}) == len(route_items)
    assert all(set(item) == {"label", "query"} for item in route_items + free_items)
