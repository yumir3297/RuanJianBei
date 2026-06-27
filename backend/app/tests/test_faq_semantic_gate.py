from app.services.qa.faq_matcher import FAQEntry
from app.services.qa.faq_semantic_gate import FAQSemanticGate


def entries() -> list[FAQEntry]:
    return [
        FAQEntry("intro", "景点介绍", ["灵山大佛介绍", "灵山大佛有什么亮点"], "", []),
        FAQEntry("location", "景点位置", ["灵山大佛位置", "灵山大佛在哪里"], "", []),
        FAQEntry("parameters", "景点参数", ["灵山大佛建筑参数", "灵山大佛有多高"], "", []),
        FAQEntry("opening", "开放信息", ["灵山大佛什么时候开放", "灵山大佛开放时间"], "", []),
        FAQEntry("overview", "景区概况", ["灵山胜境介绍"], "", []),
        FAQEntry("tips", "游览贴士", ["灵山胜境最佳游览时间"], "", []),
    ]


def build_gate() -> FAQSemanticGate:
    gate = FAQSemanticGate()
    gate.build(entries())
    return gate


def test_gate_routes_unique_entity_suffix_and_intent() -> None:
    gate = build_gate()

    parameters = gate.decide("那尊露天青铜大佛究竟有多高")
    opening = gate.decide("大佛下午几点关门")

    assert parameters.allowed_entry_ids == frozenset({"parameters"})
    assert parameters.entity == "灵山大佛"
    assert parameters.intent == "parameters"
    assert opening.allowed_entry_ids == frozenset({"opening"})


def test_gate_routes_global_overview_and_visit_time() -> None:
    gate = build_gate()

    assert gate.decide("简单介绍一下灵山胜境这个景区").allowed_entry_ids == frozenset({"overview"})
    assert gate.decide("一年里哪个季节来灵山游玩比较舒服").allowed_entry_ids == frozenset({"tips"})


def test_gate_rejects_blind_spots_and_unknown_intent() -> None:
    gate = build_gate()

    assert gate.decide("景区卫生间具体在哪里").reason == "unsupported_domain"
    assert gate.decide("灵山大佛附近有什么").reason == "unknown_spot_intent"
    assert gate.decide("讲个笑话").allowed is False
