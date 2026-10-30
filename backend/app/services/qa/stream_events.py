from __future__ import annotations

import json
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass(slots=True)
class StreamEvent:
    type: str
    data: dict = field(default_factory=dict)

    def to_sse(self) -> bytes:
        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.type}\ndata: {payload}\n\n".encode("utf-8")


async def with_sse_heartbeat(source: AsyncIterator[bytes], interval: float = 15.0) -> AsyncIterator[bytes]:
    """Keep idle transport connections alive without cancelling the producer."""
    iterator = source.__aiter__()
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(iterator.__anext__())
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield b": keepalive\n\n"
                continue
            try:
                chunk = pending.result()
            except StopAsyncIteration:
                break
            pending = None
            yield chunk
    finally:
        if pending is not None:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        close = getattr(iterator, "aclose", None)
        if close is not None:
            await close()

