from __future__ import annotations

import asyncio
import logging

from app.services.qa.stream_mux import StreamMuxState
from app.services.qa.streaming_tts_buffer import StreamingTTSBuffer

logger = logging.getLogger(__name__)


class StreamingTTSController:
    """Coordinate text chunks and finish signaling for one streaming TTS session."""

    def __init__(
        self,
        session,
        state: StreamMuxState,
        buffer: StreamingTTSBuffer,
        finish_requested: asyncio.Event,
    ) -> None:
        self._session = session
        self._state = state
        self._buffer = buffer
        self._finish_requested = finish_requested

    async def flush_ready(self) -> bool:
        if (
            self._session is None
            or not self._state.tts_connected
            or self._state.tts_failed
            or not self._buffer.ready()
        ):
            return False
        chunk = self._buffer.take_ready()
        if chunk is None:
            return False
        try:
            await self._session.send_text(chunk)
        except Exception:
            logger.exception("Streaming TTS send failed; switching to HTTP fallback")
            self._state.tts_failed = True
            self._state.tts_done = True
            return False
        return True

    async def finish_if_ready(self) -> bool:
        if (
            self._session is None
            or not self._state.llm_done
            or not self._state.tts_connected
            or self._state.tts_failed
            or self._state.tts_finish_sent
        ):
            return False
        try:
            remaining_chunk = self._buffer.drain()
            if remaining_chunk is not None:
                await self._session.send_text(remaining_chunk)
            await self._session.finish()
            self._finish_requested.set()
            self._state.tts_finish_sent = True
        except Exception:
            logger.exception("Streaming TTS finish failed; switching to HTTP fallback")
            self._state.tts_failed = True
            self._state.tts_done = True
            return False
        return True
