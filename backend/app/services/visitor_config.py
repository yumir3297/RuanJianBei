from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.avatar_config import AvatarConfig
from app.schemas.display_assets import PublicBackgroundAsset, PublicDisplayAssets, TouristDisplaySettings
from app.schemas.visitor_config import PublicAvatarConfig, PublicVisitorConfig
from app.services.display_assets import DisplayAssetService


LEGACY_VOICE_TYPES = {
    "female_warm": "gentle-female",
    "female_calm": "calm-female",
    "male_calm": "deep-male",
    "male_enthusiastic": "deep-male",
}
VALID_VOICE_TYPES = {"gentle-female", "calm-female", "deep-male", "lively-female"}
DEFAULT_AVATAR = PublicAvatarConfig(model_key="hanfu", voice_type="gentle-female")


def _public_model_key(model_path: str) -> str:
    lowered = model_path.lower()
    for model_key in ("monk", "hanfu", "modern"):
        if model_key in lowered:
            return model_key
    return "hanfu"


def _public_voice_type(value: str) -> str:
    normalized = LEGACY_VOICE_TYPES.get(value, value)
    return normalized if normalized in VALID_VOICE_TYPES else "gentle-female"


class VisitorConfigService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def read(self) -> PublicVisitorConfig:
        result = await self.session.execute(
            select(AvatarConfig)
            .where(AvatarConfig.is_active.is_(True))
            .order_by(AvatarConfig.id)
        )
        avatar = result.scalars().first()
        if avatar is None:
            result = await self.session.execute(select(AvatarConfig).order_by(AvatarConfig.id))
            avatar = result.scalars().first()

        public_avatar = DEFAULT_AVATAR
        if avatar is not None:
            public_avatar = PublicAvatarConfig(
                model_key=_public_model_key(avatar.model_path),
                voice_type=_public_voice_type(avatar.voice_type),
            )

        assets = DisplayAssetService(self.settings).get_assets(strict=True)
        display = PublicDisplayAssets(
            tourist_background=PublicBackgroundAsset(
                asset_url=assets["tourist_background"].get("asset_url"),
            ),
            welcome_text=assets["welcome_text"],
            tourist_settings=TouristDisplaySettings.model_validate(assets["tourist_settings"]),
        )
        return PublicVisitorConfig(avatar=public_avatar, display=display)
