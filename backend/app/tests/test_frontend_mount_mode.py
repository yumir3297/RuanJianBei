from __future__ import annotations

from pathlib import Path

import main
from app.core.config import Settings


def no_root_mount(app):
    return not any(route.__class__.__name__ == "Mount" and getattr(route, "name", None) == "frontend" for route in app.routes)


def test_frontend_mount_requires_serve_flag_and_legacy_root_index(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    (dist / "tourist").mkdir(parents=True)
    (dist / "admin").mkdir()
    monkeypatch.setattr(main, "legacy_frontend_dist", lambda _settings: dist)

    monkeypatch.setattr(main, "get_settings", lambda: Settings(serve_frontend=False))
    assert no_root_mount(main.create_app())

    monkeypatch.setattr(main, "get_settings", lambda: Settings(serve_frontend=True))
    assert no_root_mount(main.create_app())

    (dist / "index.html").write_text("legacy root", encoding="utf-8")
    assert not no_root_mount(main.create_app())
