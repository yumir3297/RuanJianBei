from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.knowledge import KnowledgeEntry
from app.models.quick_topic import QuickTopic
from app.models.route import RouteTemplate
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.quick_topic import QuickTopicRepository
from app.repositories.route import RouteRepository
from app.schemas.chat import ConversationContext
from app.schemas.selection import SelectionContext
from app.services.qa.guided_selector import GuidedSelectionResolver, build_selection_cache_key
from app.services.rag.base import RetrievalScope


def build_resolver():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add_all(
        [
            KnowledgeEntry(
                id=13,
                title="灵山大佛",
                category="景点信息",
                content="大佛官方资料",
                source="official.docx",
                aliases="大佛|那个大佛",
            ),
            KnowledgeEntry(
                id=16,
                title="五印坛城",
                category="景点信息",
                content="坛城官方资料",
                source="official.docx",
                aliases="坛城",
            ),
            KnowledgeEntry(
                id=34,
                title="历史文化爱好者路线（6小时深度游）",
                category="游览路线",
                content="路线官方资料",
                source="official.docx",
                aliases="历史路线",
            ),
            QuickTopic(
                key="history",
                label="历史文化",
                category="knowledge",
                icon="scroll-text",
                sort_order=10,
                is_enabled=True,
            ),
            QuickTopic(
                key="architecture",
                label="建筑艺术",
                category="knowledge",
                icon="building",
                sort_order=20,
                is_enabled=True,
            ),
            QuickTopic(
                key="disabled",
                label="已停用",
                category="knowledge",
                icon="x",
                sort_order=30,
                is_enabled=False,
            ),
            RouteTemplate(
                id="route_001",
                title="历史文化爱好者路线",
                duration_label="6小时深度游",
                route_plan="入口 -> 灵山大佛",
                source="official.docx",
                tags="历史|文化",
            ),
        ]
    )
    session.commit()
    resolver = GuidedSelectionResolver(
        KnowledgeRepository(session),
        QuickTopicRepository(session),
        RouteRepository(session),
    )
    return session, resolver


def test_query_entity_overrides_selected_attraction() -> None:
    session, resolver = build_resolver()
    try:
        resolved = resolver.resolve(
            "五印坛城有什么特色？",
            SelectionContext(mode="attraction", attraction_id=13, topic_key="history"),
        )

        assert resolved.selection.mode == "attraction"
        assert resolved.selection.attraction_id == 16
        assert resolved.selection.topic_key == "history"
        assert resolved.scope is not None
        assert resolved.scope.source_entry_id == 16
        assert resolved.resolution_source == "query"
        assert resolved.active_subject == "五印坛城"
        assert "query_entity_overrode_selection" in resolved.warnings
    finally:
        session.close()


def test_invalid_selection_is_cleared_without_creating_scope() -> None:
    session, resolver = build_resolver()
    try:
        resolved = resolver.resolve(
            "介绍一下",
            SelectionContext(
                mode="attraction",
                attraction_id=999,
                topic_key="disabled",
                route_id="missing",
            ),
        )

        assert resolved.selection.mode == "free_chat"
        assert resolved.selection.attraction_id is None
        assert resolved.selection.topic_key is None
        assert resolved.selection.route_id is None
        assert resolved.scope is None
        assert set(resolved.warnings) == {
            "invalid_attraction_id",
            "invalid_topic_key",
            "invalid_route_id",
        }
    finally:
        session.close()


def test_topic_and_route_create_only_safe_scopes() -> None:
    session, resolver = build_resolver()
    try:
        history = resolver.resolve(
            "我想了解这个主题",
            SelectionContext(mode="topic", topic_key="history"),
        )
        architecture = resolver.resolve(
            "我想了解这个主题",
            SelectionContext(mode="topic", topic_key="architecture"),
        )
        route = resolver.resolve(
            "这条路线怎么走？",
            SelectionContext(mode="route", route_id="route_001"),
        )

        assert history.scope is not None
        assert history.scope.category == "历史文化"
        assert architecture.scope is None
        assert architecture.selection.topic_key == "architecture"
        assert route.scope is not None
        assert route.scope.source_entry_id == 34
    finally:
        session.close()


def test_history_subject_is_used_only_without_valid_selection() -> None:
    session, resolver = build_resolver()
    try:
        resolved = resolver.resolve(
            "它有什么特色？",
            None,
            ConversationContext(last_subject="灵山大佛"),
        )

        assert resolved.selection.attraction_id == 13
        assert resolved.resolution_source == "history"
        assert resolved.scope is not None
        assert resolved.scope.source_entry_id == 13
    finally:
        session.close()


def test_validated_subject_is_retained_for_five_followup_turns() -> None:
    session, resolver = build_resolver()
    try:
        context = ConversationContext(last_subject="灵山大佛")
        for query in [
            "它有什么特色？",
            "参观时要注意什么？",
            "一般需要多久？",
            "适合带孩子吗？",
            "还有什么值得了解？",
        ]:
            resolved = resolver.resolve(query, None, context)
            assert resolved.selection.attraction_id == 13
            assert resolved.scope == RetrievalScope(source_entry_id=13)
            assert resolved.active_subject == "灵山大佛"
            context = ConversationContext(**resolved.to_event_data()["conversation_context"])
    finally:
        session.close()


def test_cache_key_changes_with_resolved_selection() -> None:
    query = "有什么特色"
    big_buddha = build_selection_cache_key(
        query,
        SelectionContext(mode="attraction", attraction_id=13),
    )
    mandala = build_selection_cache_key(
        query,
        SelectionContext(mode="attraction", attraction_id=16),
    )

    assert big_buddha != mandala
    assert len(big_buddha) < 255
    assert big_buddha == build_selection_cache_key(
        query,
        SelectionContext(mode="attraction", attraction_id=13),
    )
    assert big_buddha != build_selection_cache_key(
        query,
        SelectionContext(mode="attraction", attraction_id=13),
        answer_namespace="deepseek-v4-pro",
    )
