import asyncio
from types import SimpleNamespace

from app.services.qa.cached_answer_path import resolve_cached_answer


def test_cached_answer_path_skips_lookup_when_cache_is_not_allowed():
    class Cache:
        async def get(self, *args, **kwargs):
            raise AssertionError("disallowed requests must not read shared cache")

    result = asyncio.run(resolve_cached_answer(
        cache=Cache(), cache_key="key", allowed=False, epoch=3,
        epoch_is_current=lambda: asyncio.sleep(0, result=True), persona="adult",
    ))

    assert result is None


def test_cached_answer_path_reports_stale_hit_without_returning_answer():
    class Cache:
        async def get(self, key, *, epoch):
            return SimpleNamespace(answer="stale answer", sources=[{"id": "s1"}])

    result = asyncio.run(resolve_cached_answer(
        cache=Cache(), cache_key="key", allowed=True, epoch=3,
        epoch_is_current=lambda: asyncio.sleep(0, result=False), persona="adult",
    ))

    assert result.stale is True
    assert result.answer is None
    assert result.sources == []


def test_cached_answer_path_polishes_only_a_current_hit():
    class Cache:
        async def get(self, key, *, epoch):
            assert (key, epoch) == ("key", 3)
            return SimpleNamespace(answer="cached", sources=[{"id": "s1"}])

    result = asyncio.run(resolve_cached_answer(
        cache=Cache(), cache_key="key", allowed=True, epoch=3,
        epoch_is_current=lambda: asyncio.sleep(0, result=True), persona="child",
    ))

    assert result.stale is False
    assert result.answer is not None
    assert result.sources == [{"id": "s1"}]
