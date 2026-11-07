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
    queue: asyncio.Queue[tuple[bytes | None, Exception | None, bool]] = asyncio.Queue(maxsize=1)

    async def produce() -> None:
        try:
            async for chunk in iterator:
                await queue.put((chunk, None, False))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await queue.put((None, exc, True))
        else:
            await queue.put((None, None, True))
        finally:
            close = getattr(iterator, "aclose", None)
            if close is not None:
                try:
                    await close()
                except Exception:
                    pass

    producer = asyncio.create_task(produce())
    try:
        while True:
            try:
                chunk, error, finished = await asyncio.wait_for(queue.get(), timeout=interval)
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                continue

            if error is not None:
                raise error
            if finished:
                break
            if chunk is not None:
                yield chunk
    finally:
        if not producer.done():
            producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)
