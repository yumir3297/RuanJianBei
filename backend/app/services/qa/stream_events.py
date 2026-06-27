from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass(slots=True)
class StreamEvent:
    type: str
    data: dict = field(default_factory=dict)

    def to_sse(self) -> bytes:
        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.type}\ndata: {payload}\n\n".encode("utf-8")

