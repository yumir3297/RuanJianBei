from fastapi import APIRouter, Depends, Response

from app.core.config import Settings
from app.core.deps import get_app_settings
from app.schemas.display_assets import PublicBackgroundAsset, PublicDisplayAssets, TouristDisplaySettings
from app.services.display_assets import DisplayAssetService


router = APIRouter()


@router.get("/", response_model=PublicDisplayAssets)
def get_public_display_assets(
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> PublicDisplayAssets:
    # Only published visitor-facing content is public. Uploads stay on the admin router.
    assets = DisplayAssetService(settings).get_assets()
    response.headers["Cache-Control"] = "no-store"
    return PublicDisplayAssets(
        tourist_background=PublicBackgroundAsset(
            asset_url=assets["tourist_background"].get("asset_url"),
        ),
        welcome_text=assets["welcome_text"],
        tourist_settings=TouristDisplaySettings.model_validate(assets["tourist_settings"]),
    )
