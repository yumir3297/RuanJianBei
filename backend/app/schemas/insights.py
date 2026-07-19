from datetime import datetime

from pydantic import BaseModel, Field


class SpotAttentionItem(BaseModel):
    name: str
    count: int
    ratio: float


class VisitorGroupItem(BaseModel):
    group_label: str
    count: int
    ratio: float


class TagItem(BaseModel):
    tag: str
    count: int


class VisitorGroups(BaseModel):
    audience_distribution: list[VisitorGroupItem]
    top_tags: list[TagItem]


class DailyTrendItem(BaseModel):
    date: str
    count: int


class HitDistributionItem(BaseModel):
    level: str
    label: str
    count: int
    ratio: float


class QATrend(BaseModel):
    daily_trend: list[DailyTrendItem]
    hit_distribution: list[HitDistributionItem]


class BlindSpotTopItem(BaseModel):
    rank: int
    query: str
    hit_count: int


class EmotionDistributionItem(BaseModel):
    emotion: str
    label: str
    count: int
    ratio: float


class RecentEmotionItem(BaseModel):
    id: int
    query: str
    input_mode: str
    text_emotion: str
    audio_emotion: str | None = None
    fused_emotion: str
    confidence: float
    conflict: bool
    modalities: list[str] = Field(default_factory=list)
    response_strategy: str
    created_at: datetime


class EmotionInsights(BaseModel):
    total_analyzed: int
    multimodal_count: int
    conflict_count: int
    attention_count: int
    urgent_count: int
    distribution: list[EmotionDistributionItem] = Field(default_factory=list)
    recent: list[RecentEmotionItem] = Field(default_factory=list)
