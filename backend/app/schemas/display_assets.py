from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PublicBackgroundAsset(BaseModel):
    asset_url: str | None = None


class TouristModuleSetting(BaseModel):
    id: Literal["explore", "map", "route", "quiz"]
    title: str = Field(min_length=1, max_length=24)
    enabled: bool = True
    order: int = Field(ge=0, le=100)


class TouristHotlineSetting(BaseModel):
    id: Literal["broadcast", "complaint", "emergency"]
    label: str = Field(min_length=1, max_length=24)
    description: str = Field(default="", max_length=48)
    number: str = Field(min_length=3, max_length=32)
    enabled: bool = True


class TouristDisplaySettings(BaseModel):
    brand_name: str = Field(default="数字人导览", min_length=1, max_length=40)
    landing_tagline: str = Field(default="走进风景，听见这里的故事。", max_length=80)
    footer_text: str = Field(default="", max_length=120)
    guide_name: str = Field(default="", max_length=24)
    guide_subtitle: str = Field(default="数字人导游", min_length=1, max_length=40)
    primary_color: str = "#dce7d7"
    background_tint: str = "#18352b"
    background_tint_opacity: float = Field(default=0.72, ge=0.0, le=0.92)
    edge_fade_width: int = Field(default=36, ge=20, le=48)
    edge_blur: int = Field(default=20, ge=0, le=36)
    font_style: Literal["system", "serif"] = "serif"
    modules: list[TouristModuleSetting] = Field(default_factory=lambda: [
        TouristModuleSetting(id="explore", title="景点探索", order=10),
        TouristModuleSetting(id="map", title="实时地图", order=20),
        TouristModuleSetting(id="route", title="智能路线", order=30),
        TouristModuleSetting(id="quiz", title="文化故事", order=40),
    ])
    quick_questions: list[str] = Field(default_factory=lambda: [
        "有哪些值得看的景点？",
        "推荐一条游览路线",
        "这里有什么代表性的故事？",
        "附近适合拍照的景点有哪些？",
    ], max_length=8)
    hotlines: list[TouristHotlineSetting] = Field(default_factory=lambda: [
        TouristHotlineSetting(id="broadcast", label="广播找人", description="寻人广播·游客中心", number="0510-85688631"),
        TouristHotlineSetting(id="complaint", label="景区投诉", description="服务投诉建议", number="400-168-0303转5"),
        TouristHotlineSetting(id="emergency", label="医疗急救", description="紧急医疗救助", number="0510-85688120"),
    ])

    @field_validator("primary_color", "background_tint")
    @classmethod
    def validate_color(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("颜色需使用 #RRGGBB 格式")
        return value.lower()

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, modules: list[TouristModuleSetting]) -> list[TouristModuleSetting]:
        ids = [module.id for module in modules]
        if len(ids) != len(set(ids)):
            raise ValueError("导览模块不能重复")
        if not any(module.enabled for module in modules):
            raise ValueError("至少需要保留一个导览模块")
        return modules

    @field_validator("hotlines")
    @classmethod
    def validate_hotlines(cls, hotlines: list[TouristHotlineSetting]) -> list[TouristHotlineSetting]:
        ids = [hotline.id for hotline in hotlines]
        if len(ids) != len(set(ids)):
            raise ValueError("服务热线不能重复")
        return hotlines

    @field_validator("quick_questions")
    @classmethod
    def validate_quick_questions(cls, questions: list[str]) -> list[str]:
        cleaned = [question.strip() for question in questions if question.strip()]
        if len(cleaned) > 8 or any(len(question) > 80 for question in cleaned):
            raise ValueError("常用提问最多 8 条，每条不超过 80 个字")
        return cleaned


class PublicDisplayAssets(BaseModel):
    tourist_background: PublicBackgroundAsset
    welcome_text: str = ""
    tourist_settings: TouristDisplaySettings = Field(default_factory=TouristDisplaySettings)
