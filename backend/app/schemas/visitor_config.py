from typing import Literal

from pydantic import BaseModel

from app.schemas.display_assets import PublicDisplayAssets


PublicAvatarModelKey = Literal["monk", "hanfu", "modern"]
PublicAvatarVoiceType = Literal[
    "gentle-female",
    "calm-female",
    "deep-male",
    "lively-female",
]


class PublicAvatarConfig(BaseModel):
    model_key: PublicAvatarModelKey
    voice_type: PublicAvatarVoiceType


class PublicVisitorConfig(BaseModel):
    avatar: PublicAvatarConfig
    display: PublicDisplayAssets
