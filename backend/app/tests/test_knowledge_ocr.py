import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.knowledge_workspace import ParsedSection
from app.services.knowledge.ocr import parse_pdf_with_optional_ocr
from app.services.knowledge.parsers import BaseDocumentParser


class FakePDFParser(BaseDocumentParser):
    def parse(self, path: Path):
        if path.name != 'output.pdf':
            raise AppError('needs OCR', error_code='needs_ocr', status_code=422)
        assert path.read_text() == 'recognized'
        return [ParsedSection(title='页', content='识别内容', page_start=1, page_end=1, section_path='第 1 页')]


def test_ocr_is_disabled_by_default_and_does_not_run(tmp_path):
    source = tmp_path / 'source.pdf'
    source.write_text('synthetic')
    with pytest.raises(AppError) as exc:
        parse_pdf_with_optional_ocr(FakePDFParser(), source, Settings())
    assert exc.value.error_code == 'needs_ocr'


@pytest.mark.skipif(os.name != 'posix', reason='OCR subprocess isolation is POSIX only')
def test_ocr_success_marks_sections_and_failure_is_not_a_draft(tmp_path):
    source = tmp_path / 'source.pdf'
    source.write_text('synthetic')
    runner = tmp_path / 'fake-ocr'
    runner.write_text('#!/bin/sh\nfor last; do :; done\nprintf recognized > "$last"\n', encoding='utf-8')
    runner.chmod(0o755)
    settings = Settings(knowledge_ocr_enabled=True, knowledge_ocr_executable=str(runner))
    sections = parse_pdf_with_optional_ocr(FakePDFParser(), source, settings)
    assert sections[0].content == '识别内容'
    assert sections[0].extraction_method == 'ocr_mixed'
    assert source.read_text() == 'synthetic'
    runner.write_text('#!/bin/sh\nexit 1\n', encoding='utf-8')
    with pytest.raises(AppError) as exc:
        parse_pdf_with_optional_ocr(FakePDFParser(), source, settings)
    assert exc.value.error_code == 'ocr_failed'


@pytest.mark.skipif(os.name != 'posix', reason='OCR subprocess isolation is POSIX only')
def test_ocr_timeout_is_reported(tmp_path):
    source = tmp_path / 'source.pdf'
    source.write_text('synthetic')
    runner = tmp_path / 'slow-ocr'
    runner.write_text('#!/bin/sh\nsleep 20\n', encoding='utf-8')
    runner.chmod(0o755)
    settings = Settings(knowledge_ocr_enabled=True, knowledge_ocr_executable=str(runner), knowledge_ocr_timeout_seconds=1)
    with pytest.raises(AppError) as exc:
        parse_pdf_with_optional_ocr(FakePDFParser(), source, settings)
    assert exc.value.error_code == 'ocr_timeout'
