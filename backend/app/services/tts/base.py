from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TTSAudio:
    base64_audio: str
    duration_ms: int
    provider: str = "unknown"


class BaseTTSService(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> TTSAudio:
        """Convert the given text into a playable audio payload."""
