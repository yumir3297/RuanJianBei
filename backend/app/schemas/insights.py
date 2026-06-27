from pydantic import BaseModel


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
