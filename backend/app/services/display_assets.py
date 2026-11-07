from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.display_assets import TouristDisplaySettings


ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
TOURIST_BACKGROUND_KEY = "tourist_background"
WELCOME_TEXT_KEY = "welcome_text"
TOURIST_SETTINGS_KEY = "tourist_settings"

DEFAULT_WELCOME_TEXT = "欢迎来到这里，我会陪您探索景点、规划路线并了解景区服务。"


class DisplayAssetService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_root = settings.ui_asset_upload_root
        self.manifest_file = settings.ui_asset_manifest_file

    def ensure_storage(self) -> None:
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)

    def get_assets(self, *, strict: bool = False) -> dict[str, dict[str, Any]]:
        manifest = self._load_manifest(strict=strict)
        asset = manifest.get(TOURIST_BACKGROUND_KEY)
        try:
            tourist_settings = TouristDisplaySettings.model_validate(
                manifest.get(TOURIST_SETTINGS_KEY) or {}
            ).model_dump(mode="json")
        except ValidationError as error:
            if strict:
                raise self._unavailable_manifest() from error
            tourist_settings = TouristDisplaySettings().model_dump(mode="json")
        if strict and asset is not None:
            if not isinstance(asset, dict):
                raise self._unavailable_manifest()
            asset_url = asset.get("asset_url")
            if asset_url is not None and not isinstance(asset_url, str):
                raise self._unavailable_manifest()
        welcome_text = manifest.get(WELCOME_TEXT_KEY, DEFAULT_WELCOME_TEXT)
        if strict and not isinstance(welcome_text, str):
            raise self._unavailable_manifest()
        return {
            TOURIST_BACKGROUND_KEY: self._normalize_asset(asset),
            WELCOME_TEXT_KEY: welcome_text,
            TOURIST_SETTINGS_KEY: tourist_settings,
        }

    def update_tourist_settings(self, settings: TouristDisplaySettings) -> dict[str, Any]:
        self.ensure_storage()
        manifest = self._load_manifest()
        manifest[TOURIST_SETTINGS_KEY] = settings.model_dump(mode="json")
        self._save_manifest(manifest)
        return manifest[TOURIST_SETTINGS_KEY]

    def update_welcome_text(self, text: str) -> str:
        self.ensure_storage()
        manifest = self._load_manifest()
        manifest[WELCOME_TEXT_KEY] = text.strip()
        self._save_manifest(manifest)
        return manifest[WELCOME_TEXT_KEY]

    async def save_tourist_background(self, upload: UploadFile) -> dict[str, Any]:
        self.ensure_storage()

        original_name = (upload.filename or "").strip() or "tourist-background"
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            suffix = self._suffix_from_content_type(upload.content_type)
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 JPG、PNG、WEBP 格式图片。",
            )

        if upload.content_type and upload.content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图片格式不受支持。",
            )

        content = await upload.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传图片不能为空。")
        if len(content) > self.settings.ui_asset_max_image_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"图片不能超过 {self.settings.ui_asset_max_image_bytes // 1024 // 1024}MB。",
            )

        manifest = self._load_manifest()
        current_asset = self._normalize_asset(manifest.get(TOURIST_BACKGROUND_KEY))
        self._delete_relative_file(current_asset.get("relative_path"))

        relative_dir = Path("tourist-background")
        stored_name = f"tourist-background-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}{suffix}"
        relative_path = relative_dir / stored_name
        target_path = self.upload_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

        asset = {
            "asset_url": f"/ui-assets/{relative_path.as_posix()}",
            "relative_path": relative_path.as_posix(),
            "file_name": original_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest[TOURIST_BACKGROUND_KEY] = asset
        self._save_manifest(manifest)
        return self._normalize_asset(asset)

    def clear_tourist_background(self) -> dict[str, Any]:
        self.ensure_storage()
        manifest = self._load_manifest()
        current_asset = self._normalize_asset(manifest.get(TOURIST_BACKGROUND_KEY))
        self._delete_relative_file(current_asset.get("relative_path"))
        manifest[TOURIST_BACKGROUND_KEY] = {}
        self._save_manifest(manifest)
        return self._normalize_asset({})

    def _load_manifest(self, *, strict: bool = False) -> dict[str, Any]:
        try:
            self.ensure_storage()
            try:
                self.manifest_file.stat()
            except FileNotFoundError:
                return {}
            payload = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("display manifest root must be an object")
            return payload
        except (OSError, json.JSONDecodeError, ValueError) as error:
            if strict:
                raise self._unavailable_manifest() from error
            if isinstance(error, json.JSONDecodeError):
                return {}
            raise

    @staticmethod
    def _unavailable_manifest() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "display_manifest_unavailable",
                "message": "游客展示配置暂不可用，请稍后重试。",
            },
        )

    def _save_manifest(self, payload: dict[str, Any]) -> None:
        self.ensure_storage()
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.manifest_file.parent,
                prefix=f".{self.manifest_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.manifest_file)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _delete_relative_file(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        target = (self.upload_root / relative_path).resolve()
        try:
            target.relative_to(self.upload_root)
        except ValueError:
            return
        if target.exists():
            target.unlink()

    @staticmethod
    def _normalize_asset(asset: dict[str, Any] | None) -> dict[str, Any]:
        asset = asset or {}
        return {
            "asset_url": asset.get("asset_url"),
            "relative_path": asset.get("relative_path"),
            "file_name": asset.get("file_name"),
            "updated_at": asset.get("updated_at"),
        }

    @staticmethod
    def _suffix_from_content_type(content_type: str | None) -> str:
        return {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }.get((content_type or "").lower(), "")
