from __future__ import annotations

from app.services.qa.faq_matcher import FAQEntry, FAQMatcher


class FakeEmbedder:
    model_name = "fake-semantic"

    def __init__(self) -> None:
        self.batch_calls: list[list[str]] = []
        self.single_calls: list[str] = []

    def embed_texts(self, texts):
        items = list(texts)
        self.batch_calls.append(items)
        return [self._vector(text) for text in items]

    def embed(self, text: str):
        self.single_calls.append(text)
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        if "位置" in text or "哪里" in text:
            return [1.0, 0.0, 0.0]
        if "开放" in text or "几点" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def entries() -> list[FAQEntry]:
    return [
        FAQEntry("location", "景点位置", ["灵山大佛在哪里", "灵山大佛位置"], "位置答案", ["official"]),
        FAQEntry("hours", "开放信息", ["灵山大佛开放时间"], "开放答案", ["official"]),
    ]


def test_semantic_index_precomputes_aliases_and_embeds_query_once() -> None:
    embedder = FakeEmbedder()
    matcher = FAQMatcher()
    matcher.add(entries())

    matcher.ensure_semantic_index(embedder, threshold=0.8)
    result = matcher.match("大佛具体在哪里面")

    assert embedder.batch_calls == [["灵山大佛在哪里", "灵山大佛位置", "灵山大佛开放时间"]]
    assert embedder.single_calls == ["大佛具体在哪里面"]
    assert result.level == "semantic"
    assert result.entry is not None
    assert result.entry.id == "location"


def test_semantic_index_is_reused_and_rebuilt_after_reload_style_clear() -> None:
    embedder = FakeEmbedder()
    matcher = FAQMatcher()
    matcher.add(entries())

    first_build = matcher.ensure_semantic_index(embedder, threshold=0.8)
    reused = matcher.ensure_semantic_index(embedder, threshold=0.8)
    matcher.clear()
    matcher.add(entries())
    rebuilt = matcher.ensure_semantic_index(embedder, threshold=0.8)

    assert first_build >= 0.0
    assert reused == 0.0
    assert rebuilt >= 0.0
    assert len(embedder.batch_calls) == 2


def test_matcher_without_semantic_index_keeps_existing_miss_behavior() -> None:
    matcher = FAQMatcher()
    matcher.add(entries())

    result = matcher.match("完全无关的问题")

    assert result.is_hit is False
    assert result.level == "none"
