from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class AvatarPayload:
    viseme_text: str
    emotion: str = "neutral"
    action: str | None = None


class BaseAvatarService(ABC):
    @abstractmethod
    async def drive(self, text: str) -> AvatarPayload:
        """Produce the payload needed by the avatar layer."""
