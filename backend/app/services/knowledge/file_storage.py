from __future__ import annotations

import hashlib
import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError


class StoredUpload:
    def __init__(self, *, path: Path, sha256: str, size: int, original_filename: str, mime_type: str) -> None:
        self.path = path
        self.sha256 = sha256
        self.size = size
        self.original_filename = original_filename
        self.mime_type = mime_type


class KnowledgeFileStorage:
    ALLOWED_SUFFIXES = {".pdf", ".json", ".docx", ".xlsx"}

    def __init__(self, settings: Settings) -> None:
        self.root = settings.knowledge_upload_root
        self.max_file_bytes = settings.knowledge_import_max_file_bytes
        self.min_free_bytes = settings.knowledge_import_min_free_bytes

    async def store(self, upload: UploadFile) -> StoredUpload:
        original_filename = self._display_filename(upload.filename or "upload")
        suffix = Path(original_filename).suffix.lower()
        if suffix not in self.ALLOWED_SUFFIXES:
            raise AppError("Only PDF, JSON, DOCX and XLSX knowledge documents are supported.", error_code="unsupported_file_type", status_code=415)

        token = uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(self.root).free < self.min_free_bytes:
            raise AppError(
                "Knowledge upload storage is low on free space. New imports are temporarily disabled.",
                error_code="insufficient_storage",
                status_code=507,
            )
        final_path = self.root / f"{token}{suffix}"
        temporary_path = self.root / f".{token}.part"
        digest = hashlib.sha256()
        total_size = 0
        prefix = bytearray()
        try:
            with temporary_path.open("xb") as destination:
                while chunk := await upload.read(64 * 1024):
                    total_size += len(chunk)
                    if total_size > self.max_file_bytes:
                        raise AppError("The upload exceeds the configured file-size limit.", error_code="file_too_large", status_code=413)
                    if len(prefix) < 16:
                        prefix.extend(chunk[: 16 - len(prefix)])
                    digest.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            if total_size == 0:
                raise AppError("The uploaded file is empty.", error_code="empty_file", status_code=422)
            if suffix == ".pdf" and not bytes(prefix).startswith(b"%PDF-"):
                raise AppError("The file contents are not a valid PDF document.", error_code="invalid_pdf", status_code=422)
            if suffix in {".docx", ".xlsx"} and not bytes(prefix).startswith(b"PK\x03\x04"):
                raise AppError("The file contents are not a valid Office document.", error_code=f"invalid_{suffix[1:]}", status_code=422)
            if suffix == ".json":
                try:
                    temporary_path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise AppError("The JSON document must use UTF-8 encoding.", error_code="invalid_json", status_code=422) from exc
            temporary_path.replace(final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        mime_type = {".pdf": "application/pdf", ".json": "application/json", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[suffix]
        return StoredUpload(
            path=final_path,
            sha256=digest.hexdigest(),
            size=total_size,
            original_filename=original_filename,
            mime_type=mime_type,
        )

    @staticmethod
    def _display_filename(value: str) -> str:
        normalized = value.replace("\\", "/").split("/")[-1].strip()
        normalized = re.sub(r"[\x00-\x1f\x7f]", "", normalized)
        return (normalized or "upload")[:255]
