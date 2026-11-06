from app.services.capacity import CapacityLimiter


def test_capacity_rejects_overload_and_releases_once():
    limiter = CapacityLimiter({"vision": 1})
    first = limiter.try_acquire("vision")
    assert first is not None
    assert limiter.try_acquire("vision") is None
    first.release()
    first.release()
    second = limiter.try_acquire("vision")
    assert second is not None
    assert limiter.try_acquire("vision") is None
    second.release()
