import asyncio

from app.services.idempotency import IdempotencyCapacityExceeded, IdempotencyConflict, IdempotencyCoordinator


def test_concurrent_and_completed_retries_share_result():
    asyncio.run(_test_concurrent_and_completed_retries_share_result())


async def _test_concurrent_and_completed_retries_share_result():
    coordinator = IdempotencyCoordinator()
    calls = 0
    gate = asyncio.Event()

    async def operation():
        nonlocal calls
        calls += 1
        await gate.wait()
        return {"ok": True}

    first = asyncio.create_task(coordinator.run("asr", "k", "fp", operation))
    await asyncio.sleep(0)
    second = asyncio.create_task(coordinator.run("asr", "k", "fp", operation))
    await asyncio.sleep(0)
    gate.set()
    assert await asyncio.gather(first, second) == [{"ok": True}, {"ok": True}]
    assert await coordinator.run("asr", "k", "fp", operation) == {"ok": True}
    assert calls == 1


def test_conflicting_fingerprint_fails_without_running_operation():
    asyncio.run(_test_conflicting_fingerprint_fails_without_running_operation())


async def _test_conflicting_fingerprint_fails_without_running_operation():
    coordinator = IdempotencyCoordinator()
    await coordinator.run("vision", "k", "one", lambda: _value(1))
    try:
        await coordinator.run("vision", "k", "two", lambda: _value(2))
    except IdempotencyConflict:
        return
    raise AssertionError("different fingerprints must conflict")


def test_failure_not_cached_and_cancelled_waiter_does_not_cancel_owner():
    asyncio.run(_test_failure_not_cached_and_cancelled_waiter_does_not_cancel_owner())


def test_inflight_entries_are_bounded_and_completed_entries_expire():
    asyncio.run(_test_inflight_entries_are_bounded_and_completed_entries_expire())


def test_oversized_result_is_returned_but_not_cached():
    asyncio.run(_test_oversized_result_is_returned_but_not_cached())


async def _test_oversized_result_is_returned_but_not_cached():
    coordinator = IdempotencyCoordinator(max_bytes=8)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        return {"data": "too large"}

    assert await coordinator.run("vision", "large", "fp", operation) == {"data": "too large"}
    assert await coordinator.run("vision", "large", "fp", operation) == {"data": "too large"}
    assert calls == 2


async def _test_inflight_entries_are_bounded_and_completed_entries_expire():
    coordinator = IdempotencyCoordinator(ttl_seconds=0.01, max_entries=1)
    started, release = asyncio.Event(), asyncio.Event()

    async def slow():
        started.set()
        await release.wait()
        return {"ok": True}

    owner = asyncio.create_task(coordinator.run("asr", "one", "fp", slow))
    await started.wait()
    try:
        await coordinator.run("asr", "two", "fp", lambda: _value({"ok": True}))
    except IdempotencyCapacityExceeded:
        pass
    else:
        raise AssertionError("in-flight entry limit must be enforced")
    release.set()
    await owner
    await asyncio.sleep(0.02)
    calls = 0

    async def again():
        nonlocal calls
        calls += 1
        return {"ok": True}

    await coordinator.run("asr", "one", "fp", again)
    assert calls == 1


async def _test_failure_not_cached_and_cancelled_waiter_does_not_cancel_owner():
    coordinator = IdempotencyCoordinator()
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("retry")
        started.set()
        await release.wait()
        return {"ok": 2}

    try:
        await coordinator.run("asr", "k", "fp", operation)
    except RuntimeError:
        pass
    else:
        raise AssertionError("operation failure should propagate")
    owner = asyncio.create_task(coordinator.run("asr", "k", "fp", operation))
    await started.wait()
    waiter = asyncio.create_task(coordinator.run("asr", "k", "fp", operation))
    await asyncio.sleep(0)
    waiter.cancel()
    try:
        await waiter
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancelled waiter should receive cancellation")
    release.set()
    assert await owner == {"ok": 2}
    assert calls == 2


async def _value(value):
    return value
