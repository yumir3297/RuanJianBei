from __future__ import annotations

import asyncio

import pytest

from app.core.config import Settings
from app.db import deployment


def test_production_restart_does_not_migrate_or_initialize(monkeypatch):
    calls = []
    monkeypatch.setattr(deployment, "migrate_database", lambda _settings: calls.append("migrate"))

    async def initialize(_settings, *, include_demo=False):
        calls.append(("initialize", include_demo))

    monkeypatch.setattr(deployment, "initialize_database", initialize)
    settings = Settings(app_env="production", auto_migrate_on_startup=False, bootstrap_on_startup=False)
    asyncio.run(deployment.prepare_startup_database(settings))
    assert calls == []


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
