from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.display_assets import DisplayAssetService


def make_service(tmp_path):
    return DisplayAssetService(Settings(
        ui_asset_upload_dir=str(tmp_path / "uploads"),
        ui_asset_manifest_path=str(tmp_path / "display.json"),
    ))


def test_manifest_replacement_exposes_only_complete_old_or_new_json(tmp_path, monkeypatch):
    import app.services.display_assets as display_assets

    service = make_service(tmp_path)
    service.ensure_storage()
    old_value = {"welcome_text": "old", "items": [0]}
    new_value = {"welcome_text": "new", "items": [1]}
    service._save_manifest(old_value)
    original_replace = display_assets.os.replace
    replacement_ready = threading.Event()
    allow_replacement = threading.Event()
    errors = []

    def pause_replace(source, target):
        replacement_ready.set()
        assert allow_replacement.wait(timeout=2)
        original_replace(source, target)

    monkeypatch.setattr(display_assets.os, "replace", pause_replace)

    def save_new_value():
        try:
            service._save_manifest(new_value)
        except Exception as error:
            errors.append(error)

    writer = threading.Thread(target=save_new_value)
    writer.start()
    assert replacement_ready.wait(timeout=2)
    assert json.loads(service.manifest_file.read_text(encoding="utf-8")) == old_value
    temp_files = list(service.manifest_file.parent.glob(f".{service.manifest_file.name}.*.tmp"))
    assert len(temp_files) == 1
    assert json.loads(temp_files[0].read_text(encoding="utf-8")) == new_value
    allow_replacement.set()
    writer.join(timeout=2)
    assert not writer.is_alive()
    assert errors == []
    assert json.loads(service.manifest_file.read_text(encoding="utf-8")) == new_value


def test_replace_failure_preserves_previous_manifest_and_cleans_temp(tmp_path, monkeypatch):
    import app.services.display_assets as display_assets

    service = make_service(tmp_path)
    service.ensure_storage()
    old_value = {"welcome_text": "old"}
    service._save_manifest(old_value)

    def fail_replace(_source, _target):
        raise OSError("injected replace failure")

    monkeypatch.setattr(display_assets.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        service._save_manifest({"welcome_text": "new"})

    assert json.loads(service.manifest_file.read_text(encoding="utf-8")) == old_value
    assert list(service.manifest_file.parent.glob(f".{service.manifest_file.name}.*.tmp")) == []


def test_strict_manifest_read_rejects_corrupt_existing_file_but_defaults_when_missing(tmp_path):
    service = make_service(tmp_path)
    service.ensure_storage()
    assert service.get_assets(strict=True)["welcome_text"]

    service.manifest_file.write_text("{broken", encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        service.get_assets(strict=True)
    assert error.value.status_code == 503


def test_strict_manifest_read_rejects_invalid_settings_in_existing_file(tmp_path):
    service = make_service(tmp_path)
    service.ensure_storage()
    service.manifest_file.write_text(
        '{"tourist_settings":{"primary_color":"not-a-color"}}', encoding="utf-8"
    )
    with pytest.raises(HTTPException) as error:
        service.get_assets(strict=True)
    assert error.value.status_code == 503


def test_strict_manifest_read_reports_unreadable_file(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    service.ensure_storage()
    service.manifest_file.write_text("{}", encoding="utf-8")
    original_read_text = Path.read_text

    def denied(path, *args, **kwargs):
        if path == service.manifest_file:
            raise PermissionError("injected unreadable manifest")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(HTTPException) as error:
        service.get_assets(strict=True)
    assert error.value.status_code == 503
