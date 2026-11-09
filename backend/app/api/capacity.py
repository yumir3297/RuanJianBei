from fastapi import HTTPException, Request, status
from threading import Lock

from app.core.config import Settings
from app.services.capacity import CapacityLease, CapacityLimiter

_initialization_lock = Lock()


def acquire_capacity(request: Request, settings: Settings, name: str) -> CapacityLease:
    limiter = getattr(request.app.state, "guide_capacity", None)
    if limiter is None:
        with _initialization_lock:
            limiter = getattr(request.app.state, "guide_capacity", None)
            if limiter is None:
                limiter = CapacityLimiter({
                    "chat": settings.chat_max_active,
                    "asr": settings.asr_max_active,
                    "vision": settings.vision_max_active,
                })
                request.app.state.guide_capacity = limiter
    lease = limiter.try_acquire(name)
    if lease is None:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="服务繁忙，请稍后再试。", headers={"Retry-After": "5"})
    return lease
