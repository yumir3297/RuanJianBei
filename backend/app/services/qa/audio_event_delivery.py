from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

from app.services.qa.stream_events import StreamEvent


class AudioEventDelivery:
    """Publish drained speech events while enforcing cancellation and epoch stop."""

    def __init__(self, drainer, cancel_audio: Callable[[], Awaitable[None]]) -> None:
        self.drainer = drainer
        self.cancel_audio = cancel_audio
        self.visibility_changed = False

    async def events(self) -> AsyncIterator[StreamEvent]:
        try:
            async for event in self.drainer.events():
                yield event
        except BaseException:
            await self.cancel_audio()
            raise

        self.visibility_changed = self.drainer.visibility_changed
        if self.visibility_changed:
            yield StreamEvent(type="error", data={"message": "知识内容已更新，已停止继续输出。"})
