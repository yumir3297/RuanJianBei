from __future__ import annotations

from datetime import datetime

from app.core.config import Settings
from app.models.knowledge import KnowledgeEntry
from app.schemas.live_data import AttractionLiveStatus, LiveContext


class LiveDataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_context(self, attractions: list[KnowledgeEntry]) -> LiveContext:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        statuses = [
            AttractionLiveStatus(
                attraction_id=str(entry.id),
                name=entry.title,
                status="开放",
                note="当前为演示模拟数据",
            )
            for entry in attractions[:8]
        ]
        return LiveContext(
            is_mock=self.settings.live_data_provider == "mock",
            source_label=self.settings.live_data_provider,
            weather={
                "condition": self.settings.live_data_mock_weather,
                "temperature": self.settings.live_data_mock_temperature,
                "suggestion": "适合户外与室内景点搭配游览",
            },
            visitor_flow={
                "level": self.settings.live_data_mock_crowd_level,
                "suggestion": "高峰景点建议错峰进入",
            },
            attractions_status=statuses,
            timestamp=timestamp,
        )
