from app.schemas.selection import SelectionContext
from app.services.qa.guided_selector import build_selection_cache_key


def _sel():
    return SelectionContext(mode="attraction", attraction_id=13)


def test_cache_key_differs_by_audience():
    base = build_selection_cache_key("灵山大佛有多高", _sel(), answer_namespace="ns")
    child = build_selection_cache_key(
        "灵山大佛有多高", _sel(), answer_namespace="ns", audience="child"
    )
    expert = build_selection_cache_key(
        "灵山大佛有多高", _sel(), answer_namespace="ns", audience="expert"
    )
    assert base != child
    assert child != expert
    assert base != expert


def test_cache_key_is_stable_for_same_inputs():
    first = build_selection_cache_key(
        "灵山大佛有多高", _sel(), answer_namespace="ns", audience="child"
    )
    second = build_selection_cache_key(
        "灵山大佛有多高", _sel(), answer_namespace="ns", audience="child"
    )
    assert first == second


def test_cache_key_prefix_bumped_to_v4():
    key = build_selection_cache_key("灵山大佛有多高", _sel(), answer_namespace="ns")
    assert key.startswith("qa:v4:")


def test_cache_key_unchanged_when_audience_absent_vs_adult():
    without = build_selection_cache_key("大佛", _sel(), answer_namespace="ns")
    adult = build_selection_cache_key("大佛", _sel(), answer_namespace="ns", audience="adult")
    assert without == adult
