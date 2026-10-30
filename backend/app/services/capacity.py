"""Per-process concurrent-work limits; deployment-wide limits belong at the edge."""
from threading import Lock


class CapacityLease:
    def __init__(self, limiter: "CapacityLimiter", name: str) -> None:
        self._limiter = limiter
        self._name = name
        self._released = False

    def release(self) -> None:
        with self._limiter._lock:
            if not self._released:
                self._released = True
                self._limiter._active[self._name] -= 1


class CapacityLimiter:
    def __init__(self, limits: dict[str, int]) -> None:
        self._limits = dict(limits)
        self._active = {name: 0 for name in limits}
        self._lock = Lock()

    def try_acquire(self, name: str) -> CapacityLease | None:
        with self._lock:
            if self._active[name] >= self._limits[name]:
                return None
            self._active[name] += 1
            return CapacityLease(self, name)
