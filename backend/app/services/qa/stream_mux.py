from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


async def get_epoch_guarded_message(
    queue: asyncio.Queue[tuple[str, object | None]],
    epoch_is_current: Callable[[], Awaitable[bool]],
) -> tuple[str, object | None] | None:
    """Read one mux message only while its request knowledge epoch stays current."""
    if not await epoch_is_current():
        return None
    message = await queue.get()
    if not await epoch_is_current():
        return None
    return message


@dataclass
class MuxDelivery:
    has_llm_payload: bool = False
    llm_payload: object | None = None
    tts_payload: object | None = None
    drain_audio: bool = False
    llm_error: Exception | None = None
    warning: str | None = None


class StreamMuxState:
    """Track producer lifecycle and route mux messages to the response loop."""

    def __init__(self, *, streaming_requested: bool) -> None:
        self.llm_done = False
        self.llm_error: Exception | None = None
        self.tts_connected = False
        self.tts_done = not streaming_requested
        self.tts_failed = False
        self.tts_finish_sent = False
        self.tts_confirmed_chars = 0

    def consume(self, kind: str, payload: object | None) -> MuxDelivery:
        if kind == "llm":
            return MuxDelivery(has_llm_payload=True, llm_payload=payload)
        if kind == "llm_error":
            error = payload if isinstance(payload, Exception) else RuntimeError("LLM stream failed")
            self.llm_error = error
            return MuxDelivery(llm_error=error)
        if kind == "llm_done":
            self.llm_done = True
        elif kind == "tts_connected":
            self.tts_connected = True
        elif kind == "tts_connect_error":
            self.tts_failed = True
            self.tts_done = True
            return MuxDelivery(warning="connect")
        elif kind == "tts":
            event = payload
            event_type = getattr(event, "type", "")
            if event_type == "word_timestamps":
                timestamp_data = getattr(event, "data", {}) or {}
                if isinstance(timestamp_data, dict):
                    self.tts_confirmed_chars = max(
                        self.tts_confirmed_chars,
                        int(timestamp_data.get("characters", 0) or 0),
                    )
            if event_type == "error":
                self.tts_failed = True
                self.tts_done = True
                return MuxDelivery(warning="mid_response")
            if event_type == "done":
                self.tts_done = True
                return MuxDelivery()
            return MuxDelivery(tts_payload=event)
        elif kind == "audio_ready":
            return MuxDelivery(drain_audio=True)
        return MuxDelivery()
