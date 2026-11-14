from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from zipfile import ZipFile

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
            missing_pages: list[int] = []
            for index, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    missing_pages.append(index)
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

        if missing_pages:
            pages = ", ".join(map(str, missing_pages[:20]))
            suffix = "…" if len(missing_pages) > 20 else ""
            raise AppError(
                f"PDF 第 {pages}{suffix} 页无法提取文本，请核查是否为空白页或先进行 OCR 后再导入。",
                error_code="needs_ocr",
                status_code=422,
            )
        if not sections:
            raise AppError(
                "This PDF contains no extractable text and needs OCR.",
                error_code="needs_ocr",
                status_code=422,
            )
        return sections


class DOCXKnowledgeParser(BaseDocumentParser):
    """Extract body paragraphs and simple tables in order into reviewable drafts."""

    def parse(self, path: Path) -> list[ParsedSection]:
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise AppError("DOCX parser dependency is unavailable.", error_code="docx_dependency_missing", status_code=503) from exc
        try:
            with ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > 5000 or sum(item.file_size for item in members) > 64 * 1024 * 1024:
                    raise AppError("DOCX 解压后内容过大，请拆分文件后重试。", error_code="document_too_large", status_code=413)
                if "word/document.xml" not in archive.namelist():
                    raise AppError("DOCX 缺少正文，请检查文件。", error_code="invalid_docx", status_code=422)
            document = Document(str(path))
            if document.element.body.xpath('.//w:drawing | .//w:pict | .//w:object'):
                raise AppError("DOCX 正文包含图片或嵌入对象，请先人工提取并核查后导入。", error_code="needs_ocr", status_code=422)
            sections: list[ParsedSection] = []
            title, lines, start = None, [], 1

            def flush():
                if lines:
                    section_path = f"正文第 {start} 块"
                    sections.append(ParsedSection(title=(title or section_path)[:200], content="\n".join(lines), section_path=section_path))

            for index, block in enumerate(document.iter_inner_content(), start=1):
                if isinstance(block, Paragraph):
                    text = block.text.strip()
                    if not text:
                        continue
                    style = (block.style.name or "").casefold() if block.style else ""
                    if style.startswith("heading") or style.startswith("标题"):
                        flush()
                        lines = []
                        title, start = text, index
                    else:
                        lines.append(text)
                elif isinstance(block, Table):
                    if block._tbl.xpath('.//w:gridSpan | .//w:vMerge'):
                        raise AppError("DOCX 包含合并单元格，请先人工整理后导入。", error_code="unsupported_docx_structure", status_code=422)
                    for row in block.rows:
                        if any(cell.tables for cell in row.cells):
                            raise AppError("DOCX 包含嵌套表格，请先人工整理后导入。", error_code="unsupported_docx_structure", status_code=422)
                        cells = [" ".join(p.text.strip() for p in cell.paragraphs if p.text.strip()) for cell in row.cells]
                        if any(cells):
                            lines.append(" | ".join(cells))
            flush()
        except AppError:
            raise
        except Exception as exc:
            raise AppError("DOCX 文档无法解析，请检查文件。", error_code="invalid_docx", status_code=422) from exc
        if not sections:
            raise AppError("DOCX 正文没有可读取的文字。", error_code="empty_document", status_code=422)
        return sections


class XLSXKnowledgeParser(BaseDocumentParser):
    """Import plain rows using the first nonempty row as column labels."""

    def parse(self, path: Path) -> list[ParsedSection]:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise AppError("XLSX parser dependency is unavailable.", error_code="xlsx_dependency_missing", status_code=503) from exc
        try:
            with ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > 5000 or sum(item.file_size for item in members) > 64 * 1024 * 1024:
                    raise AppError("XLSX 解压后内容过大，请拆分文件后重试。", error_code="document_too_large", status_code=413)
                if "xl/workbook.xml" not in archive.namelist():
                    raise AppError("XLSX 缺少工作簿，请检查文件。", error_code="invalid_xlsx", status_code=422)
            workbook = load_workbook(filename=path, data_only=False, read_only=False, keep_links=False)
            try:
                if sum(sheet.max_row * sheet.max_column for sheet in workbook.worksheets) > 100_000:
                    raise AppError("XLSX 单元格范围过大，请拆分文件后重试。", error_code="document_too_large", status_code=413)
                sections: list[ParsedSection] = []
                for sheet in workbook.worksheets:
                    if sheet.merged_cells.ranges or sheet._images or sheet._charts:
                        raise AppError(f"工作表 {sheet.title} 包含合并单元格、图片或图表，请先人工整理。", error_code="unsupported_xlsx_structure", status_code=422)
                    headers = None
                    for row in sheet.iter_rows():
                        if any(cell.data_type in {"f", "e"} for cell in row):
                            raise AppError(f"工作表 {sheet.title} 第 {row[0].row} 行包含公式或错误值，请先核对并转换为确定的值。", error_code="unsupported_xlsx_formula", status_code=422)
                        cells = [str(cell.value).strip() if cell.value is not None else "" for cell in row]
                        if not any(cells):
                            continue
                        if headers is None:
                            headers = cells
                            nonempty = [value.casefold() for value in headers if value]
                            if len(nonempty) != len(set(nonempty)):
                                raise AppError(f"工作表 {sheet.title} 表头重复，请先整理。", error_code="invalid_xlsx_header", status_code=422)
                            continue
                        if any(value and not headers[index] for index, value in enumerate(cells)):
                            raise AppError(f"工作表 {sheet.title} 第 {row[0].row} 行存在没有表头的数据列。", error_code="invalid_xlsx_header", status_code=422)
                        pairs = [f"{headers[index]}: {value}" for index, value in enumerate(cells) if value]
                        if pairs:
                            row_number = row[0].row
                            title = cells[0] or f"{sheet.title} 第 {row_number} 行"
                            if len(sections) >= 2000:
                                raise AppError("XLSX 数据行过多，请拆分文件后重试。", error_code="document_too_large", status_code=413)
                            sections.append(ParsedSection(title=title[:200], content="\n".join(pairs), section_path=f"{sheet.title}!{row_number}"))
            finally:
                workbook.close()
        except AppError:
            raise
        except Exception as exc:
            raise AppError("XLSX 文件无法解析，请检查文件。", error_code="invalid_xlsx", status_code=422) from exc
        if not sections:
            raise AppError("XLSX 没有可读取的数据行。", error_code="empty_document", status_code=422)
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
    if suffix == ".docx":
        return DOCXKnowledgeParser()
    if suffix == ".xlsx":
        return XLSXKnowledgeParser()
    raise AppError("Only PDF, JSON, DOCX and XLSX knowledge documents are supported.", error_code="unsupported_file_type", status_code=415)
