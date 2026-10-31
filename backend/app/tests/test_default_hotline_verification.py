from app.schemas.display_assets import TouristDisplaySettings

def test_unverified_default_hotlines_are_not_enabled():
    assert all(not hotline.enabled for hotline in TouristDisplaySettings().hotlines)
