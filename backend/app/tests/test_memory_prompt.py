from app.services.memory.profile import build_memory_prompt


def _memory(**overrides):
    base = {
        "visitor_id": "v-1",
        "visit_count": 1,
        "visited_attractions": [],
        "preference_tags": [],
        "narration_audience": "adult",
    }
    base.update(overrides)
    return base


def test_returns_empty_for_missing_memory():
    assert build_memory_prompt(None) == ""
    assert build_memory_prompt({}) == ""


def test_returns_empty_for_first_visit_without_signals():
    assert build_memory_prompt(_memory(visit_count=1)) == ""


def test_first_visit_with_attractions_still_produces_profile():
    text = build_memory_prompt(_memory(visit_count=1, visited_attractions=["灵山大佛"]))
    assert "已经游览过" in text
    assert "灵山大佛" in text
    assert "欢迎回来" not in text, "首次到访不应说欢迎回来"


def test_repeat_visitor_gets_welcome_back_line():
    text = build_memory_prompt(
        _memory(visit_count=2, visited_attractions=["灵山大佛", "灵山梵宫"])
    )
    assert "第 2 次" in text
    assert "欢迎回来" in text
    assert "灵山梵宫" in text


def test_audience_preference_is_rendered():
    child = build_memory_prompt(_memory(visit_count=2, narration_audience="child"))
    assert "孩子能听懂" in child


def test_prompt_forbids_treating_memory_as_fact():
    text = build_memory_prompt(_memory(visit_count=2, visited_attractions=["灵山大佛"]))
    assert "不要把记忆当作景区事实依据" in text


def test_attractions_are_capped():
    many = [f"景点{i}" for i in range(20)]
    text = build_memory_prompt(_memory(visit_count=2, visited_attractions=many))
    assert text.count("景点") <= 8
