from pathlib import Path

from app.services.qa.faq_matcher import FAQMatcher


def test_faq_matcher_exact() -> None:
    matcher = FAQMatcher()
    matcher.load_from_file(Path(__file__).resolve().parents[3] / "data" / "processed" / "faq_entries.json")

    result = matcher.match("灵山大佛有多高")

    assert result.is_hit is True
    assert result.level == "exact"
    assert "88" in result.answer
