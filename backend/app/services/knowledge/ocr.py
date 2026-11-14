from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import threading
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.knowledge.parsers import BaseDocumentParser

_OCR_LOCK = threading.BoundedSemaphore(1)


def parse_pdf_with_optional_ocr(parser: BaseDocumentParser, source: Path, settings: Settings):
    try:
        return parser.parse(source)
    except AppError as exc:
        if exc.error_code != "needs_ocr" or not settings.knowledge_ocr_enabled:
            raise
    executable = Path(settings.knowledge_ocr_executable)
    if os.name != "posix" or not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
        raise AppError("本地 OCR 未配置可执行程序，请联系管理员。", error_code="ocr_unavailable", status_code=503)
    if not _OCR_LOCK.acquire(timeout=min(10, max(1, settings.knowledge_import_parse_timeout_seconds - 2))):
        raise AppError("本地 OCR 正忙，请稍后重试。", error_code="ocr_busy", status_code=503)
    try:
        return _run_ocr(parser, source, settings, executable)
    finally:
        _OCR_LOCK.release()


def _run_ocr(parser: BaseDocumentParser, source: Path, settings: Settings, executable: Path):
    with tempfile.TemporaryDirectory(prefix="knowledge-ocr-") as directory:
        output = Path(directory) / "output.pdf"
        args = [str(executable), "--skip-text", "--output-type", "pdf", "--jobs", "1",
                "--ocr-engine", settings.knowledge_ocr_engine, "-l", settings.knowledge_ocr_language,
                str(source), str(output)]
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        env["PATH"] = f"{executable.parent}{os.pathsep}{env.get('PATH', '')}"
        try:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, env=env, start_new_session=True)
            try:
                code = process.wait(timeout=min(settings.knowledge_ocr_timeout_seconds, max(1, settings.knowledge_import_parse_timeout_seconds - 12)))
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise AppError("本地 OCR 超时，请拆分文档或稍后重试。", error_code="ocr_timeout", status_code=422) from exc
        except OSError as exc:
            raise AppError("本地 OCR 启动失败，请检查配置。", error_code="ocr_unavailable", status_code=503) from exc
        if code != 0 or not output.is_file():
            raise AppError("本地 OCR 未能识别该文件，请人工处理后重试。", error_code="ocr_failed", status_code=422)
        sections = parser.parse(output)
        return [section.model_copy(update={"extraction_method": "ocr_mixed"}) for section in sections]
