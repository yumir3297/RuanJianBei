from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.exceptions import AppError
from app.schemas.knowledge_workspace import ParsedSection


class BaseDocumentParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> list[ParsedSection]:
        raise NotImplementedError


class PDFTextParser(BaseDocumentParser):
    def __init__(self, max_pages: int = 500) -> None:
        self.max_pages = max_pages

    def parse(self, path: Path) -> list[ParsedSection]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise AppError("PDF parser dependency is unavailable.", error_code="pdf_dependency_missing", status_code=503) from exc

        try:
            reader = PdfReader(str(path), strict=True)
            if reader.is_encrypted:
                try:
                    decrypted = reader.decrypt("")
                except Exception:
                    decrypted = 0
                if not decrypted:
                    raise AppError("The PDF is password-protected.", error_code="encrypted_pdf", status_code=422)
            if len(reader.pages) > self.max_pages:
                raise AppError("The PDF exceeds the configured page limit.", error_code="too_many_pages", status_code=413)
            sections: list[ParsedSection] = []
            for index, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                title = (lines[0] if lines else f"第 {index} 页")[:200]
                sections.append(
                    ParsedSection(
                        title=title,
                        content="\n".join(lines),
                        page_start=index,
                        page_end=index,
                        section_path=f"第 {index} 页",
                    )
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError("The PDF could not be parsed.", error_code="invalid_pdf", status_code=422) from exc

        if not sections:
            raise AppError(
                "This PDF contains no extractable text and needs OCR.",
                error_code="needs_ocr",
                status_code=422,
            )
        return sections


class JSONKnowledgeParser(BaseDocumentParser):
    def parse(self, path: Path) -> list[ParsedSection]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError("The JSON document is invalid.", error_code="invalid_json", status_code=422) from exc
        if isinstance(payload, dict):
            payload = payload.get("entries")
        if not isinstance(payload, list):
            raise AppError("JSON knowledge must be an array or contain an entries array.", error_code="invalid_json_shape", status_code=422)

        sections: list[ParsedSection] = []
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            content = str(item.get("content") or "").strip()
            if not title or not content:
                continue
            stable_id = str(item.get("stable_id") or item.get("id") or "").strip() or None
            section_path = str(item.get("section_path") or "").strip() or None
            sections.append(
                ParsedSection(
                    title=title[:200],
                    content=content,
                    section_path=section_path or f"条目 {index}",
                    stable_id=stable_id,
                )
            )
        if not sections:
            raise AppError("The JSON document contains no valid knowledge entries.", error_code="empty_document", status_code=422)
        return sections


def parser_for_path(path: Path, max_pages: int = 500) -> BaseDocumentParser:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PDFTextParser(max_pages=max_pages)
    if suffix == ".json":
        return JSONKnowledgeParser()
    raise AppError("Only PDF and JSON knowledge documents are supported.", error_code="unsupported_file_type", status_code=415)
