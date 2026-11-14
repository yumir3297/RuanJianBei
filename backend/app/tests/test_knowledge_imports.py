from __future__ import annotations

import asyncio
import io

from fastapi import UploadFile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.api.knowledge_imports import router as imports_router
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import ImportBatch, ImportConflict, ImportJob, KnowledgeRevision, SourceDocument, SourceDocumentVersion
from app.schemas.knowledge_workspace import ParsedSection
from app.services.knowledge.imports import KnowledgeImportService
from app.services.knowledge.parsers import BaseDocumentParser
from app.services.knowledge.parsers import JSONKnowledgeParser, PDFTextParser
from app.tests.async_db import open_test_session


class FakeParser(BaseDocumentParser):
    def parse(self, path):
        payload = path.read_bytes()
        if b"SCAN" in payload:
            from app.core.exceptions import AppError

            raise AppError("OCR needed.", error_code="needs_ocr", status_code=422)
        if b"ENCRYPTED" in payload:
            from app.core.exceptions import AppError

            raise AppError("Encrypted PDF.", error_code="encrypted_pdf", status_code=422)
        return [
            ParsedSection(
                title="灵山大佛",
                content="灵山大佛是景区地标。",
                page_start=1,
                page_end=1,
                section_path="第 1 页",
            )
        ]


def _upload(filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
    from starlette.datastructures import Headers

    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def test_batch_imports_are_independent_and_create_persistent_drafts(tmp_path) -> None:
    db_path = str(tmp_path / "imports.db")
    settings = Settings(knowledge_upload_dir=str(tmp_path / "files"))

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgeImportService(session, settings, parser=FakeParser())
            batch = await service.create_import(
                [_upload("good.pdf", b"%PDF-1.7 GOOD"), _upload("bad.pdf", b"%PDF-1.7 ENCRYPTED")],
                document_ids=[None, None],
                idempotency_key="upload-two-pdfs",
            )
            assert len(batch.jobs) == 2
            await service.run_import(batch.jobs[0].id)
            await service.run_import(batch.jobs[1].id)

            stored_batch = await service.get_batch(batch.id)
            jobs = stored_batch.jobs
            assert stored_batch.state == "partial"
            assert [job.state for job in jobs] == ["succeeded", "failed"]
            assert jobs[1].error and "encrypted_pdf" in jobs[1].error
            entries = list((await session.execute(select(KnowledgeEntry))).scalars().all())
            assert len(entries) == 1
            assert entries[0].published_revision_id is None
            revision = await session.get(KnowledgeRevision, entries[0].draft_revision_id)
            assert revision is not None and revision.page_start == 1 and revision.page_end == 1
            assert revision.source_document_version_id is not None
            assert (await session.scalar(select(SourceDocument.name))) == "good.pdf"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_same_document_hash_is_not_parsed_or_drafted_twice(tmp_path) -> None:
    db_path = str(tmp_path / "imports-duplicate.db")
    settings = Settings(knowledge_upload_dir=str(tmp_path / "files"))

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgeImportService(session, settings, parser=FakeParser())
            first = await service.create_import(
                [_upload("manual.pdf", b"%PDF-1.7 SAME")], document_ids=[None], idempotency_key="first-pdf"
            )
            await service.run_import(first.jobs[0].id)
            first_batch = await service.get_batch(first.id)
            source_version = await session.get(SourceDocumentVersion, first_batch.jobs[0].document_version_id)
            document_id = source_version.document_id

            second = await service.create_import(
                [_upload("renamed.pdf", b"%PDF-1.7 SAME")],
                document_ids=[document_id],
                idempotency_key="same-content-again",
            )
            assert second.jobs[0].state == "succeeded"
            assert second.jobs[0].stage == "unchanged"
            assert await session.scalar(select(KnowledgeRevision.id).limit(2)) is not None
            revisions = list((await session.execute(select(KnowledgeRevision))).scalars().all())
            assert len(revisions) == 1
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_reimport_updates_matching_draft_and_preserves_conflicts(tmp_path) -> None:
    db_path = str(tmp_path / "imports-revision.db")
    settings = Settings(knowledge_upload_dir=str(tmp_path / "files"))

    class ChangingParser(BaseDocumentParser):
        def parse(self, path):
            content = path.read_bytes().decode("utf-8").split("|", 1)[1]
            return [ParsedSection(title="展馆", content=content, section_path="展馆/一层")]

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgeImportService(session, settings, parser=ChangingParser())
            first = await service.create_import(
                [_upload("guide.json", '{"entries":[]}|原始讲解'.encode())], document_ids=[None], idempotency_key="v1"
            )
            await service.run_import(first.jobs[0].id)
            entry = (await session.execute(select(KnowledgeEntry))).scalar_one()
            first_draft = entry.draft_revision_id

            second = await service.create_import(
                [_upload("guide.json", '{"entries":[]}|修订讲解'.encode())],
                document_ids=[first.jobs[0].document_version_id and (await session.get(SourceDocumentVersion, first.jobs[0].document_version_id)).document_id],
                idempotency_key="v2",
            )
            await service.run_import(second.jobs[0].id)
            await session.refresh(entry)
            assert entry.draft_revision_id != first_draft
            updated = await session.get(KnowledgeRevision, entry.draft_revision_id)
            assert updated.content == "修订讲解"

            # A later human draft wins over a source update; the imported version is retained as a conflict.
            from app.services.knowledge.workspace import KnowledgeWorkspaceService
            from app.schemas.knowledge import KnowledgeUpdate
            _, human_draft = await KnowledgeWorkspaceService(session).save_draft(
                entry.id,
                KnowledgeUpdate(content="人工编辑"),
                expected_version=entry.lock_version,
            )
            assert human_draft.source_document_version_id == second.jobs[0].document_version_id
            assert human_draft.section_path == "展馆/一层"
            from app.api.knowledge import _to_knowledge_read
            presented = _to_knowledge_read(entry, human_draft)
            assert presented.source_document_version_id == human_draft.source_document_version_id
            assert presented.section_path == "展馆/一层"
            third = await service.create_import(
                [_upload("guide.json", '{"entries":[]}|第三版'.encode())],
                document_ids=[(await session.get(SourceDocumentVersion, second.jobs[0].document_version_id)).document_id],
                idempotency_key="v3",
            )
            await service.run_import(third.jobs[0].id)
            await session.refresh(entry)
            current = await session.get(KnowledgeRevision, entry.draft_revision_id)
            assert current.content == "人工编辑"
            conflicts = list((await session.execute(select(ImportConflict))).scalars().all())
            assert len(conflicts) == 1
            incoming = await session.get(KnowledgeRevision, conflicts[0].incoming_revision_id)
            assert incoming.content == "第三版"
            from app.core.exceptions import AppError
            from app.schemas.knowledge_workspace import ImportConflictResolution
            from app.services.knowledge.publication import KnowledgePublicationService

            try:
                await KnowledgePublicationService(session).create_publication(
                    [{"entry_id": entry.id, "revision_id": entry.draft_revision_id, "expected_version": entry.lock_version}],
                    idempotency_key="blocked-by-import-conflict",
                )
            except AppError as exc:
                assert exc.error_code == "pending_import_conflict"
            else:
                raise AssertionError("pending source conflicts must block publication")

            await service.resolve_conflict(
                conflicts[0].id,
                ImportConflictResolution(choice="use_incoming", expected_version=entry.lock_version),
            )
            await session.refresh(entry)
            assert entry.draft_revision_id == incoming.id
            assert (await session.get(ImportConflict, conflicts[0].id)).state == "resolved"
            _, replaced_source = await KnowledgeWorkspaceService(session).save_draft(
                entry.id, KnowledgeUpdate(source="人工指定的新来源"), expected_version=entry.lock_version,
            )
            assert replaced_source.source_document_version_id is None
            assert replaced_source.section_path is None
            import json
            assert "source_document_id" not in json.loads(replaced_source.metadata_json or "{}")
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_batch_idempotency_and_path_like_filename_do_not_duplicate_or_escape_storage(tmp_path) -> None:
    db_path = str(tmp_path / "imports-idempotent.db")
    storage_root = tmp_path / "private-files"
    settings = Settings(knowledge_upload_dir=str(storage_root))

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgeImportService(session, settings, parser=FakeParser())
            first = await service.create_import(
                [_upload("../../secrets.pdf", b"%PDF-1.7 SAFE")],
                document_ids=[None],
                idempotency_key="same-batch",
            )
            second = await service.create_import(
                [_upload("again.pdf", b"%PDF-1.7 OTHER")],
                document_ids=[None],
                idempotency_key="same-batch",
            )
            assert first.id == second.id
            assert list(storage_root.rglob("*"))
            assert all(path.resolve().is_relative_to(storage_root.resolve()) for path in storage_root.rglob("*"))
            assert await session.scalar(select(ImportBatch.id).limit(2)) == first.id
            assert len(list((await session.execute(select(ImportJob))).scalars().all())) == 1
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_admin_upload_api_returns_batch_and_per_file_status(tmp_path) -> None:
    db_path = str(tmp_path / "imports-api.db")
    settings = Settings(knowledge_upload_dir=str(tmp_path / "api-files"))
    app = FastAPI()
    app.include_router(imports_router, prefix="/api/knowledge-imports")

    async def override_session():
        engine, session = await open_test_session(db_path)
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_app_settings] = lambda: settings
    token = create_admin_token(get_settings().admin_token_secret)
    client = TestClient(app)

    response = client.post(
        "/api/knowledge-imports/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "api-upload"},
        files=[("files", ("guide.pdf", b"%PDF-1.7 TEXT", "application/pdf"))],
    )
    assert response.status_code == 202
    batch = response.json()
    assert batch["state"] == "queued"
    assert batch["jobs"][0]["filename"] == "guide.pdf"
    assert batch["jobs"][0]["document_id"]

    restored = client.get(
        f"/api/knowledge-imports/{batch['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert restored.status_code == 200
    assert restored.json()["jobs"][0]["document_version_id"] == batch["jobs"][0]["document_version_id"]
    recent = client.get("/api/knowledge-imports/recent", headers={"Authorization": f"Bearer {token}"})
    assert recent.status_code == 200
    assert recent.json()[0]["id"] == batch["id"]


def test_real_pdf_text_parser_preserves_page_numbers_and_flags_scan_only_files(tmp_path) -> None:
    from pypdf import PdfWriter
    from app.core.exceptions import AppError

    # Small valid PDF using a built-in font keeps this test independent of OCR/font assets.
    content = b"BT /F1 12 Tf 72 720 Td (Hello PDF) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    text_pdf = tmp_path / "text.pdf"
    text_pdf.write_bytes(pdf)
    sections = PDFTextParser().parse(text_pdf)
    assert sections[0].title == "Hello PDF"
    assert sections[0].content == "Hello PDF"
    assert sections[0].page_start == sections[0].page_end == 1

    mixed_writer = PdfWriter()
    mixed_writer.append(str(text_pdf))
    mixed_writer.add_blank_page(width=612, height=792)
    mixed_path = tmp_path / "mixed.pdf"
    with mixed_path.open("wb") as output:
        mixed_writer.write(output)
    try:
        PDFTextParser().parse(mixed_path)
    except AppError as exc:
        assert exc.error_code == "needs_ocr"
        assert "2" in str(exc)
    else:
        raise AssertionError("a partially extractable PDF must not silently omit pages")

    async def import_mixed_pdf() -> None:
        engine, session = await open_test_session(str(tmp_path / "mixed-import.db"))
        settings = Settings(knowledge_upload_dir=str(tmp_path / "mixed-files"))
        try:
            service = KnowledgeImportService(session, settings)
            batch = await service.create_import([_upload("mixed.pdf", mixed_path.read_bytes())], idempotency_key="mixed")
            await service.run_import(batch.jobs[0].id)
            job = (await service.get_batch(batch.id)).jobs[0]
            assert job.stage == "needs_ocr"
            assert "2" in job.error
            assert not (await session.scalars(select(KnowledgeEntry))).all()
            version = await session.get(SourceDocumentVersion, job.document_version_id)
            assert version.parse_status == "needs_ocr"
            assert (settings.knowledge_upload_root / version.storage_path).is_file()
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(import_mixed_pdf())

    scan_writer = PdfWriter()
    scan_writer.add_blank_page(width=612, height=792)
    scan_path = tmp_path / "scan.pdf"
    with scan_path.open("wb") as output:
        scan_writer.write(output)
    try:
        PDFTextParser().parse(scan_path)
    except AppError as exc:
        assert exc.error_code == "needs_ocr"
    else:
        raise AssertionError("an image-only/blank PDF must not be reported as parsed successfully")

    encrypted_writer = PdfWriter()
    encrypted_writer.add_blank_page(width=612, height=792)
    encrypted_writer.encrypt("secret")
    encrypted_path = tmp_path / "encrypted.pdf"
    with encrypted_path.open("wb") as output:
        encrypted_writer.write(output)
    try:
        PDFTextParser().parse(encrypted_path)
    except AppError as exc:
        assert exc.error_code == "encrypted_pdf"
    else:
        raise AssertionError("encrypted PDFs must be reported with a retryable error")


def test_json_parser_requires_nonempty_entries(tmp_path) -> None:
    from app.core.exceptions import AppError

    path = tmp_path / "knowledge.json"
    path.write_text('{"entries":[{"title":"景点","content":"介绍"},{"title":"缺正文"}]}', encoding="utf-8")
    sections = JSONKnowledgeParser().parse(path)
    assert len(sections) == 1
    assert sections[0].title == "景点"
    path.write_text('{"entries":[]}', encoding="utf-8")
    try:
        JSONKnowledgeParser().parse(path)
    except AppError as exc:
        assert exc.error_code == "empty_document"
    else:
        raise AssertionError("empty JSON must not silently succeed")


def test_docx_import_preserves_body_and_table_order_as_unpublished_drafts(tmp_path) -> None:
    from docx import Document
    from app.services.knowledge.parsers import DOCXKnowledgeParser

    document = Document()
    document.add_heading("景点介绍", level=1)
    document.add_paragraph("第一段正文")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "开放时间"
    table.rows[0].cells[1].text = "演示时间"
    document.add_paragraph("表格后的正文")
    document.add_heading("参观提示", level=1)
    document.add_paragraph("第二节正文")
    path = tmp_path / "source.docx"
    document.save(path)
    sections = DOCXKnowledgeParser().parse(path)
    assert [item.title for item in sections] == ["景点介绍", "参观提示"]
    assert sections[0].content == "第一段正文\n开放时间 | 演示时间\n表格后的正文"
    assert sections[0].section_path == "正文第 1 块"

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "docx.db"))
        try:
            settings = Settings(knowledge_upload_dir=str(tmp_path / "docx-files"))
            service = KnowledgeImportService(session, settings)
            batch = await service.create_import([_upload("source.docx", path.read_bytes())], idempotency_key="docx-import")
            await service.run_import(batch.jobs[0].id)
            job = (await service.get_batch(batch.id)).jobs[0]
            assert job.state == "succeeded"
            entries = (await session.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.id))).all()
            assert len(entries) == 2 and all(entry.published_revision_id is None for entry in entries)
            revision = await session.get(KnowledgeRevision, entries[0].draft_revision_id)
            assert revision.content == sections[0].content and revision.section_path == sections[0].section_path
            assert revision.source_document_version_id == job.document_version_id
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_docx_nested_table_is_rejected_instead_of_silently_dropped(tmp_path) -> None:
    import pytest
    from docx import Document
    from app.core.exceptions import AppError
    from app.services.knowledge.parsers import DOCXKnowledgeParser

    document = Document()
    document.add_paragraph("正文")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).add_table(rows=1, cols=1).cell(0, 0).text = "嵌套内容"
    path = tmp_path / "nested.docx"
    document.save(path)
    with pytest.raises(AppError) as exc:
        DOCXKnowledgeParser().parse(path)
    assert exc.value.error_code == "unsupported_docx_structure"

    from docx.oxml import OxmlElement
    illustrated = Document()
    illustrated.add_paragraph("正文").add_run()._r.append(OxmlElement("w:drawing"))
    image_path = tmp_path / "illustrated.docx"
    illustrated.save(image_path)
    with pytest.raises(AppError) as image_exc:
        DOCXKnowledgeParser().parse(image_path)
    assert image_exc.value.error_code == "needs_ocr"

    merged = Document()
    merged.add_paragraph("正文")
    row = merged.add_table(rows=1, cols=2).rows[0]
    row.cells[0].merge(row.cells[1]).text = "合并内容"
    merged_path = tmp_path / "merged.docx"
    merged.save(merged_path)
    with pytest.raises(AppError) as merged_exc:
        DOCXKnowledgeParser().parse(merged_path)
    assert merged_exc.value.error_code == "unsupported_docx_structure"


def test_xlsx_import_preserves_rows_and_source_as_unpublished_drafts(tmp_path) -> None:
    from openpyxl import Workbook
    from app.services.knowledge.parsers import XLSXKnowledgeParser

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "景点"
    sheet.append([])
    sheet.append(["名称", "说明"])
    sheet.append(["合成景点", "合成资料"])
    sheet.append([])
    sheet.append(["第二景点", "第二条资料"])
    path = tmp_path / "source.xlsx"
    workbook.save(path)
    sections = XLSXKnowledgeParser().parse(path)
    assert [section.section_path for section in sections] == ["景点!3", "景点!5"]
    assert sections[0].content == "名称: 合成景点\n说明: 合成资料"

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "xlsx.db"))
        try:
            service = KnowledgeImportService(session, Settings(knowledge_upload_dir=str(tmp_path / "xlsx-files")))
            batch = await service.create_import([_upload("source.xlsx", path.read_bytes())], idempotency_key="xlsx-import")
            await service.run_import(batch.jobs[0].id)
            job = (await service.get_batch(batch.id)).jobs[0]
            assert job.state == "succeeded"
            entries = (await session.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.id))).all()
            assert len(entries) == 2 and all(entry.published_revision_id is None for entry in entries)
            revision = await session.get(KnowledgeRevision, entries[0].draft_revision_id)
            assert revision.content == sections[0].content and revision.section_path == "景点!3"
            assert revision.source_document_version_id == job.document_version_id
            first_draft = entries[0].draft_revision_id
            source_version = await session.get(SourceDocumentVersion, job.document_version_id)
            sheet.insert_rows(3)
            sheet.cell(3, 1, "插入景点")
            sheet.cell(3, 2, "插入资料")
            workbook.save(path)
            rerun = await service.create_import([_upload("source.xlsx", path.read_bytes())], document_ids=[source_version.document_id], idempotency_key="xlsx-reimport")
            await service.run_import(rerun.jobs[0].id)
            await session.refresh(entries[0])
            assert entries[0].draft_revision_id == first_draft
            assert (await session.get(KnowledgeRevision, first_draft)).content == sections[0].content
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_xlsx_formula_merged_cells_and_unlabelled_values_are_rejected(tmp_path) -> None:
    import pytest
    from openpyxl import Workbook
    from app.core.exceptions import AppError
    from app.services.knowledge.parsers import XLSXKnowledgeParser

    for kind in ("formula", "merged", "unlabelled"):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["名称", "说明" if kind != "unlabelled" else None])
        sheet.append(["景点", "=1+1" if kind == "formula" else "资料"])
        if kind == "merged":
            sheet.merge_cells("A2:B2")
        path = tmp_path / f"{kind}.xlsx"
        workbook.save(path)
        with pytest.raises(AppError) as exc:
            XLSXKnowledgeParser().parse(path)
        assert exc.value.error_code == {"formula": "unsupported_xlsx_formula", "merged": "unsupported_xlsx_structure", "unlabelled": "invalid_xlsx_header"}[kind]


def test_scanned_pdf_is_preserved_with_needs_ocr_state(tmp_path) -> None:
    db_path = str(tmp_path / "imports-scan.db")
    settings = Settings(knowledge_upload_dir=str(tmp_path / "files"))

    async def scenario() -> None:
        engine, session = await open_test_session(db_path)
        try:
            service = KnowledgeImportService(session, settings, parser=FakeParser())
            batch = await service.create_import(
                [_upload("scan.pdf", b"%PDF-1.7 SCAN")], document_ids=[None], idempotency_key="scan-pdf"
            )
            await service.run_import(batch.jobs[0].id)
            result = await service.get_batch(batch.id)
            assert result.jobs[0].state == "failed"
            assert result.jobs[0].stage == "needs_ocr"
            assert result.jobs[0].document_version_id is not None
            version = await session.get(SourceDocumentVersion, result.jobs[0].document_version_id)
            assert version.parse_status == "needs_ocr"
            assert (settings.knowledge_upload_root / version.storage_path).is_file()
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_upload_size_limit_is_enforced_without_leaving_partial_files(tmp_path) -> None:
    from app.core.exceptions import AppError
    from app.services.knowledge.file_storage import KnowledgeFileStorage

    settings = Settings(
        knowledge_upload_dir=str(tmp_path / "too-large"),
        knowledge_import_max_file_bytes=1024,
    )

    async def scenario() -> None:
        storage = KnowledgeFileStorage(settings)
        try:
            await storage.store(_upload("oversized.pdf", b"%PDF-1.7" + b"x" * 1024))
        except AppError as exc:
            assert exc.error_code == "file_too_large"
        else:
            raise AssertionError("oversized uploads must be rejected")
        assert not list(settings.knowledge_upload_root.glob("*"))

    asyncio.run(scenario())


def test_upload_is_rejected_when_storage_reserve_is_below_threshold(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace
    from app.core.exceptions import AppError
    from app.services.knowledge import file_storage
    from app.services.knowledge.file_storage import KnowledgeFileStorage

    settings = Settings(
        knowledge_upload_dir=str(tmp_path / "low-space"),
        knowledge_import_min_free_bytes=1024,
    )
    monkeypatch.setattr(file_storage.shutil, "disk_usage", lambda _: SimpleNamespace(free=100))

    async def scenario() -> None:
        storage = KnowledgeFileStorage(settings)
        try:
            await storage.store(_upload("guide.pdf", b"%PDF-1.7 CONTENT"))
        except AppError as exc:
            assert exc.error_code == "insufficient_storage"
            assert exc.status_code == 507
        else:
            raise AssertionError("imports must stop when the configured storage reserve is unavailable")
        assert not list(settings.knowledge_upload_root.glob("*"))

    asyncio.run(scenario())
