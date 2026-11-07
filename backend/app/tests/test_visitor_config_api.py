from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker


def build_app(db_path, settings):
    import main
    from app.core.deps import get_app_settings, get_db_session
    from app.tests.async_db import open_test_session

    app = main.create_app()
    engine, initial_session = asyncio.run(open_test_session(str(db_path)))
    asyncio.run(initial_session.close())
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = get_session
    app.dependency_overrides[get_app_settings] = lambda: settings
    return app, engine, factory


@pytest.mark.parametrize("config_rows, expected", [
    ([(5, "/models/modern.vrm", "female_warm", False),
      (2, "/models/monk.vrm", "male_calm", True)],
     {"model_key": "monk", "voice_type": "deep-male"}),
    ([(3, "/private/path/custom.vrm", "unknown-voice", True)],
     {"model_key": "hanfu", "voice_type": "gentle-female"}),
])
def test_anonymous_reads_active_config_without_admin_token(tmp_path, config_rows, expected):
    from app.core.config import Settings
    from app.models.avatar_config import AvatarConfig

    settings = Settings(
        ui_asset_upload_dir=str(tmp_path / "uploads"),
        ui_asset_manifest_path=str(tmp_path / "display.json"),
    )
    settings.ui_asset_manifest_file.parent.mkdir(parents=True, exist_ok=True)
    settings.ui_asset_manifest_file.write_text(
        '{"welcome_text":"欢迎游客","tourist_settings":{"brand_name":"湖区导览"}}',
        encoding="utf-8",
    )
    app, engine, factory = build_app(tmp_path / "visitor-config.db", settings)

    async def scenario():
        async with factory() as session:
            for config_id, model_path, voice, active in config_rows:
                session.add(AvatarConfig(
                    id=config_id, name=f"internal-{config_id}", model_path=model_path,
                    preview_url="/private/preview", voice_type=voice, is_active=active,
                ))
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/visitor-config")
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            body = response.json()
            assert body["avatar"] == expected
            assert body["display"]["welcome_text"] == "欢迎游客"
            assert body["display"]["tourist_settings"]["brand_name"] == "湖区导览"
            serialized = response.text
            for private_value in ("model_path", "preview_url", "internal-", "/private/path", "secret"):
                assert private_value not in serialized

            # Opening the public endpoint must not weaken legacy admin endpoints.
            for path in ("/api/admin/avatar-configs", "/api/admin/avatar-configs/active"):
                assert (await client.get(path)).status_code == 401
            assert (await client.put("/api/admin/avatar-configs/2", json={"voice_type": "deep-male"})).status_code == 401
        await engine.dispose()

    asyncio.run(scenario())


def test_missing_avatar_and_manifest_use_public_defaults(tmp_path):
    from app.core.config import Settings

    settings = Settings(
        ui_asset_upload_dir=str(tmp_path / "uploads"),
        ui_asset_manifest_path=str(tmp_path / "missing.json"),
    )
    app, engine, _factory = build_app(tmp_path / "empty-config.db", settings)

    async def scenario():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/visitor-config")
            assert response.status_code == 200
            assert response.json()["avatar"] == {"model_key": "hanfu", "voice_type": "gentle-female"}
            assert response.json()["display"]["welcome_text"]
        await engine.dispose()

    asyncio.run(scenario())


def test_corrupt_existing_manifest_fails_public_config_instead_of_serving_defaults(tmp_path):
    from app.core.config import Settings

    manifest = tmp_path / "display.json"
    manifest.write_text("{broken", encoding="utf-8")
    settings = Settings(
        ui_asset_upload_dir=str(tmp_path / "uploads"),
        ui_asset_manifest_path=str(manifest),
    )
    app, engine, _factory = build_app(tmp_path / "broken-config.db", settings)

    async def scenario():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/visitor-config")
            assert response.status_code == 503
        await engine.dispose()

    asyncio.run(scenario())


def test_uses_lowest_id_avatar_when_none_is_active(tmp_path):
    from app.core.config import Settings
    from app.models.avatar_config import AvatarConfig

    settings = Settings(
        ui_asset_upload_dir=str(tmp_path / "uploads"),
        ui_asset_manifest_path=str(tmp_path / "display.json"),
    )
    app, engine, factory = build_app(tmp_path / "inactive-config.db", settings)

    async def scenario():
        async with factory() as session:
            session.add_all([
                AvatarConfig(id=8, name="later", model_path="/models/modern.vrm",
                             voice_type="male_enthusiastic", is_active=False),
                AvatarConfig(id=3, name="first", model_path="/models/monk.vrm",
                             voice_type="female_calm", is_active=False),
            ])
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/visitor-config")
            assert response.status_code == 200
            assert response.json()["avatar"] == {"model_key": "monk", "voice_type": "calm-female"}
        await engine.dispose()

    asyncio.run(scenario())
