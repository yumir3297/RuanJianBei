from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass(frozen=True, slots=True)
class LLMStreamEvent:
    type: Literal["content", "usage", "finish"]
    text: str = ""
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str | None = None
