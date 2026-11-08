from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.api.auth import create_admin_token
from app.core.config import Settings
from app.core.deps import get_app_settings


def test_runtime_limits_requires_admin_and_returns_only_configured_limits():
    settings = Settings(
        knowledge_import_max_files=3,
        knowledge_import_max_file_bytes=12_345,
        ui_asset_max_image_bytes=67_890,
        llm_api_key="must-not-leak",
    )
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/admin")
    app.dependency_overrides[get_app_settings] = lambda: settings
    client = TestClient(app)

    anonymous = client.get("/api/admin/runtime-limits")
    assert anonymous.status_code == 401

    token = create_admin_token(settings.admin_token_secret)
    response = client.get("/api/admin/runtime-limits", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {
        "knowledge_import": {"max_files": 3, "max_file_bytes": 12_345},
        "display_assets": {"max_image_bytes": 67_890},
    }
