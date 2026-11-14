import asyncio

import pytest

from app.core.config import Settings


def test_production_rejects_default_admin_password_and_token_secret():
    settings = Settings(app_env="production")
    assert set(settings.production_security_failures) == {
        "default_admin_password",
        "weak_admin_password",
        "default_admin_token_secret",
        "weak_admin_token_secret",
    }


def test_production_accepts_custom_password_and_long_token_secret():
    settings = Settings(
        app_env="prod",
        admin_password="strong-enough-password",
        admin_token_secret="randomly-generated-secret-that-is-long-enough-123456",
    )
    assert settings.production_security_failures == ()


def test_production_rejects_explicit_synthetic_embedding_model():
    settings = Settings(
        app_env="production",
        admin_password="strong-enough-password",
        admin_token_secret="randomly-generated-secret-that-is-long-enough-123456",
        embedding_model_name="simple-dev-embedder",
    )
    assert settings.production_security_failures == ("synthetic_embedding_model",)


def test_development_keeps_local_defaults_working():
    settings = Settings(app_env="development")
    assert settings.production_security_failures == ()


def test_production_lifespan_fails_before_startup_with_unsafe_secrets(monkeypatch):
    import main

    monkeypatch.setattr(main, "get_settings", lambda: Settings(app_env="production"))

    async def enter_lifespan():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="default_admin_token_secret") as exc:
        asyncio.run(enter_lifespan())
    assert "a5-scenic-admin-secret-key" not in str(exc.value)
