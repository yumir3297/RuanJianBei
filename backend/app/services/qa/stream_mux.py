from __future__ import annotations

from dataclasses import dataclass


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
        self.tts_text_buffer = ""
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
