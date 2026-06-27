from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings


ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
TOURIST_BACKGROUND_KEY = "tourist_background"


class DisplayAssetService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_root = settings.ui_asset_upload_root
        self.manifest_file = settings.ui_asset_manifest_file

    def ensure_storage(self) -> None:
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)

    def get_assets(self) -> dict[str, dict[str, Any]]:
        manifest = self._load_manifest()
        asset = manifest.get(TOURIST_BACKGROUND_KEY)
        return {
            TOURIST_BACKGROUND_KEY: self._normalize_asset(asset),
        }

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

    def _load_manifest(self) -> dict[str, Any]:
        self.ensure_storage()
        if not self.manifest_file.exists():
            return {}
        try:
            return json.loads(self.manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_manifest(self, payload: dict[str, Any]) -> None:
        self.manifest_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
