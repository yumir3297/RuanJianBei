from __future__ import annotations

import asyncio

import pytest

from app.core.config import Settings
from app.db import deployment


def test_production_restart_does_not_migrate_or_initialize(monkeypatch):
    calls = []
    monkeypatch.setattr(deployment, "migrate_database", lambda _settings: calls.append("migrate"))
    monkeypatch.setattr(deployment, "check_schema_head", lambda _settings: calls.append("check-schema") or "current-head")

    async def initialize(_settings, *, include_demo=False):
        calls.append(("initialize", include_demo))

    monkeypatch.setattr(deployment, "initialize_database", initialize)
    settings = Settings(app_env="production", auto_migrate_on_startup=False, bootstrap_on_startup=False)
    asyncio.run(deployment.prepare_startup_database(settings))
    assert calls == ["check-schema"]


def test_production_lifespan_rejects_incompatible_schema_before_model_startup(monkeypatch, tmp_path):
    from sqlalchemy import create_engine, text
    import main as app_main
    from app.api import chat

    database = tmp_path / "old-lifespan.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('old-revision')"))
    engine.dispose()

    settings = Settings(
        app_env="production",
        auto_migrate_on_startup=False,
        bootstrap_on_startup=False,
        database_url=f"sqlite+aiosqlite:///{database}",
        admin_password="local-test-password-2026",
        admin_token_secret="local-test-signing-key-at-least-32-bytes",
        ui_asset_upload_dir=str(tmp_path / "ui-assets"),
        ui_asset_manifest_path=str(tmp_path / "config" / "display.json"),
        knowledge_upload_dir=str(tmp_path / "knowledge-uploads"),
    )
    monkeypatch.setattr(app_main, "get_settings", lambda: settings)
    monkeypatch.setattr(chat, "get_cached_embedder", lambda *_args, **_kwargs: pytest.fail("model startup ran before schema check"))
    monkeypatch.setattr(chat, "get_cached_reranker", lambda *_args, **_kwargs: pytest.fail("model startup ran before schema check"))

    async def start_lifespan():
        async with app_main.lifespan(app_main.app):
            pytest.fail("incompatible production schema must not start")

    with pytest.raises(RuntimeError, match="does not match application head"):
        asyncio.run(start_lifespan())


def test_development_startup_preserves_optional_migration_and_demo_bootstrap(monkeypatch):
    calls = []
    monkeypatch.setattr(deployment, "migrate_database", lambda _settings: calls.append("migrate"))

    async def initialize(_settings, *, include_demo=False):
        calls.append(("initialize", include_demo))

    monkeypatch.setattr(deployment, "initialize_database", initialize)
    settings = Settings(app_env="development", enable_sample_data=True)
    asyncio.run(deployment.prepare_startup_database(settings))
    assert calls == ["migrate", ("initialize", True)]


def test_production_initializer_never_seeds_demo_data_even_if_requested(monkeypatch):
    from app.db import bootstrap

    calls = []
    async def basic(*_args, **_kwargs):
        calls.append("basic")
    async def demo(*_args, **_kwargs):
        calls.append("demo")

    monkeypatch.setattr(deployment, "bootstrap_quick_topics", basic)
    monkeypatch.setattr(deployment, "bootstrap_avatar_configs", basic)
    monkeypatch.setattr(deployment, "bootstrap_sample_data", demo)
    monkeypatch.setattr(deployment, "bootstrap_experience_demo_feedback", demo)
    asyncio.run(deployment.initialize_database(Settings(app_env="production"), include_demo=True))
    assert calls == ["basic", "basic"]


def test_schema_head_check_fails_without_auto_upgrade(tmp_path):
    from sqlalchemy import create_engine, text

    database = tmp_path / "old.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('old-revision')"))
    engine.dispose()

    with pytest.raises(RuntimeError, match="schema revision"):
        deployment.check_schema_head(Settings(database_url=f"sqlite+aiosqlite:///{database}"))


def test_schema_head_check_returns_verified_single_head_after_migration(tmp_path):
    database = tmp_path / "current.sqlite"
    settings = Settings(database_url=f"sqlite+aiosqlite:///{database}")
    deployment.migrate_database(settings)
    revision = deployment.check_schema_head(settings)
    assert revision
    assert revision == "c2a8e17f5b40"


@pytest.mark.parametrize("previous", ["91a0c5e2f347", "6f0ecdb27c41", "bd17a3f492c0"])
def test_guideloop_merge_upgrades_both_prior_histories_without_losing_data(tmp_path, previous):
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    database = tmp_path / f"{previous}.sqlite"
    settings = Settings(database_url=f"sqlite+aiosqlite:///{database}")
    command.upgrade(deployment._alembic_config(settings), previous)
    engine = create_engine(deployment.migration_database_url(settings))
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE merge_sentinel (value VARCHAR(40) NOT NULL)"))
        connection.execute(text("INSERT INTO merge_sentinel (value) VALUES ('preserve')"))
    engine.dispose()
    deployment.migrate_database(settings)
    assert deployment.check_schema_head(settings) == "c2a8e17f5b40"
    engine = create_engine(deployment.migration_database_url(settings))
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT value FROM merge_sentinel")).scalar_one() == "preserve"
        assert "guide_loop_cases" in inspect(engine).get_table_names()
        assert {"knowledge_entry_id", "knowledge_revision_id"} <= {column["name"] for column in inspect(engine).get_columns("guide_loop_revisions")}
        assert "tour_sessions" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_cli_import_does_not_import_main():
    import subprocess
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "import app.cli.deployment, sys; assert 'main' not in sys.modules"],
        cwd=backend_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_check_schema_prints_verified_head_without_migrating(monkeypatch, capsys):
    from app.cli import deployment as cli

    monkeypatch.setattr(cli, "get_settings", lambda: Settings())
    monkeypatch.setattr(cli, "check_schema_head", lambda _settings: "verified-head")
    monkeypatch.setattr(cli, "migrate_database", lambda _settings: (_ for _ in ()).throw(AssertionError("must not migrate")))

    assert cli.main(["check-schema"]) == 0
    assert capsys.readouterr().out.strip() == "verified-head"
