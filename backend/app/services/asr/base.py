from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class ASRCandidate:
    text: str
    confidence: float


@dataclass(slots=True)
class ASRResult:
    text: str
    confidence: float = 1.0
    candidates: list[ASRCandidate] = field(default_factory=list)
    duration_ms: int = 0
    provider: str = "unknown"
    confidence_source: str = "provider"
    error_message: str = ""

    @property
    def needs_confirmation(self) -> bool:
        if not self.text.strip():
            return True
        if self.confidence_source in {"stub", "unavailable"}:
            return True
        return self.confidence < 0.85


class BaseASRService(ABC):
    @abstractmethod
    async def transcribe(self, content: bytes | str) -> ASRResult:
        """Transcribe the given voice payload."""
