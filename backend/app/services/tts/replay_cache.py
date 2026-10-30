"""Small process-local TTL/LRU cache for repeated historical answer replays."""

from __future__ import annotations

from collections import OrderedDict
from time import monotonic
from typing import Callable

from app.services.tts.base import TTSAudio


class ReplayAudioCache:
    def __init__(
        self,
        *,
        max_entries: int = 128,
        max_bytes: int = 16 * 1024 * 1024,
        ttl_seconds: float = 1800,
        clock: Callable[[], float] = monotonic,
    ):
        self.max_entries = max(int(max_entries), 1)
        self.max_bytes = max(int(max_bytes), 1)
        self.ttl_seconds = max(float(ttl_seconds), 0)
        self.clock = clock
        self._entries: OrderedDict[str, tuple[float, TTSAudio, int]] = OrderedDict()
        self.total_bytes = 0

    @property
    def size(self) -> int:
        return len(self._entries)

    def _remove(self, key: str) -> None:
        entry = self._entries.pop(key, None)
        if entry is not None:
            self.total_bytes -= entry[2]

    def _purge_expired(self, now: float) -> None:
        for key, (expires_at, _audio, _size) in list(self._entries.items()):
            if expires_at <= now:
                self._remove(key)

    def get(self, key):
        now = self.clock()
        self._purge_expired(now)
        entry = self._entries.get(key)
        if entry is None:
            return None
        self._entries.move_to_end(key)
        return entry[1]

    def put(self, key, audio):
        if not audio.base64_audio or self.ttl_seconds == 0:
            return
        encoded_size = len(audio.base64_audio.encode("ascii", errors="ignore"))
        if encoded_size > self.max_bytes:
            return
        now = self.clock()
        self._purge_expired(now)
        self._remove(key)
        while self._entries and (
            len(self._entries) >= self.max_entries
            or self.total_bytes + encoded_size > self.max_bytes
        ):
            oldest = next(iter(self._entries))
            self._remove(oldest)
        self._entries[key] = (now + self.ttl_seconds, audio, encoded_size)
        self.total_bytes += encoded_size
