from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

# Keep backend-relative paths such as sqlite:///./app.db and .env aligned with the app.
os.chdir(BACKEND_ROOT)

from app.api.chat import build_pipeline, close_cached_llm_service  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.schemas.chat import ChatRequest  # noqa: E402
from app.services.vision.qwen import QwenVisionService  # noqa: E402


DEFAULT_QUESTION = "请根据这张图片识别出的线索，基于官方资料介绍它最可能对应的景区景点。"


@dataclass(slots=True)
class VisionPart:
    ok: bool
    provider: str
    model: str
    elapsed_ms: float
    scene_summary: str = ""
    detected_text: str = ""
    candidate_attractions: list[str] = field(default_factory=list)
    visual_tags: list[str] = field(default_factory=list)
    query_hints: list[str] = field(default_factory=list)
    retrieval_query: str = ""
    confidence: float = 0.0
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class QAPart:
    ok: bool
    elapsed_ms: float
    query: str = ""
    answer: str = ""
    event_types: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    has_inline_citation: bool = False
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class VisionRAGSmokeReport:
    ok: bool
    image_path: str
    image_bytes: int
    mime_type: str
    session_id: str
    vision: VisionPart
    qa: QAPart


def load_settings(args: argparse.Namespace) -> Settings:
    return Settings(
        _env_file=BACKEND_ROOT / ".env",
        _env_file_encoding="utf-8",
        vision_read_timeout_seconds=args.vision_read_timeout,
        vision_total_timeout_seconds=args.vision_total_timeout,
    )


def validate_settings(settings: Settings) -> list[str]:
    missing: list[str] = []
    if settings.vision_provider.strip().lower() != "qwen":
        missing.append("VISION_PROVIDER=qwen")
    if not settings.vision_api_key.strip():
        missing.append("VISION_API_KEY")
    if not settings.vision_base_url.strip():
        missing.append("VISION_BASE_URL")
    if not settings.vision_model.strip():
        missing.append("VISION_MODEL")
    if settings.llm_provider.strip().lower() == "stub":
        missing.append("LLM_PROVIDER must not be stub for a real closed-loop smoke")
    if not settings.llm_api_key.strip():
        missing.append("LLM_API_KEY")
    if not settings.llm_base_url.strip():
        missing.append("LLM_BASE_URL")
    if not settings.llm_model.strip():
        missing.append("LLM_MODEL")
    return missing


async def analyze_image(
    image_path: Path,
    settings: Settings,
    question: str,
) -> VisionPart:
    content = image_path.read_bytes()
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    service = QwenVisionService(settings)
    started_at = perf_counter()
    try:
        result = await service.analyze(
            content,
            filename=image_path.name,
            mime_type=mime_type,
            prompt="请识别这张景区图片，输出可用于官方资料检索的景点、OCR、视觉标签和线索。",
        )
    finally:
        await service.aclose()

    elapsed_ms = (perf_counter() - started_at) * 1000
    provider_error_type = result.raw.get("error_type") if isinstance(result.raw, dict) else None
    provider_error_message = result.raw.get("error_message") if isinstance(result.raw, dict) else None
    retrieval_query = result.as_retrieval_query(question)
    has_signal = bool(
        result.scene_summary.strip()
        or result.detected_text.strip()
        or result.candidate_attractions
        or result.visual_tags
        or result.query_hints
    )
    return VisionPart(
        ok=bool(retrieval_query.strip()) and has_signal and not provider_error_type,
        provider=result.provider,
        model=settings.vision_model,
        elapsed_ms=elapsed_ms,
        scene_summary=result.scene_summary,
        detected_text=result.detected_text,
        candidate_attractions=list(result.candidate_attractions),
        visual_tags=list(result.visual_tags),
        query_hints=list(result.query_hints),
        retrieval_query=retrieval_query,
        confidence=result.confidence,
        error_type=str(provider_error_type) if provider_error_type else None,
        error_message=str(provider_error_message) if provider_error_message else None,
    )


def build_qa_query(vision: VisionPart, question: str) -> str:
    return (
        f"{question}\n"
        "图片识别线索如下，仅用于检索官方资料，不作为事实来源：\n"
        f"{vision.retrieval_query}"
    )


async def run_qa_pipeline(settings: Settings, query: str, session_id: str) -> QAPart:
    started_at = perf_counter()
    event_types: list[str] = []
    sources: list[dict[str, Any]] = []
    evidence_ids: list[str] = []
    answer_parts: list[str] = []
    answer = ""
    session = SessionLocal()
    try:
        pipeline = build_pipeline(session, settings)
        request = ChatRequest(
            query=query,
            session_id=session_id,
            input_mode="text",
            text_only=True,
        )
        async for event in pipeline.stream_chat(request):
            event_types.append(event.type)
            if event.type == "sources":
                docs = event.data.get("docs", [])
                if isinstance(docs, list):
                    sources = [doc for doc in docs if isinstance(doc, dict)]
                    evidence_ids = [
                        str(doc.get("evidence_id"))
                        for doc in sources
                        if doc.get("evidence_id")
                    ]
            elif event.type == "text_chunk":
                token = str(event.data.get("token") or "")
                if token:
                    answer_parts.append(token)
            elif event.type == "text":
                answer = str(event.data.get("text") or "")
    except Exception as exc:
        return QAPart(
            ok=False,
            elapsed_ms=(perf_counter() - started_at) * 1000,
            query=query,
            answer=answer or "".join(answer_parts),
            event_types=event_types,
            sources=sources,
            evidence_ids=evidence_ids,
            has_inline_citation="[证据" in (answer or "".join(answer_parts)),
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
        )
    finally:
        session.close()
        await close_cached_llm_service()

    final_answer = answer or "".join(answer_parts)
    has_inline_citation = "[证据" in final_answer
    ok = bool(final_answer.strip()) and bool(sources) and has_inline_citation and "done" in event_types
    return QAPart(
        ok=ok,
        elapsed_ms=(perf_counter() - started_at) * 1000,
        query=query,
        answer=final_answer,
        event_types=event_types,
        sources=sources,
        evidence_ids=evidence_ids,
        has_inline_citation=has_inline_citation,
    )


async def run_smoke(args: argparse.Namespace) -> VisionRAGSmokeReport:
    if not args.allow_network:
        raise PermissionError("Refusing to run real vision-to-RAG smoke without --allow-network.")
    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    settings = load_settings(args)
    missing = validate_settings(settings)
    if missing:
        raise ValueError(f"Missing or invalid settings: {', '.join(missing)}")

    content = image_path.read_bytes()
    if len(content) > settings.vision_max_image_bytes:
        raise ValueError(
            f"Image is too large: {len(content)} bytes > {settings.vision_max_image_bytes} bytes"
        )

    vision = await analyze_image(image_path, settings, args.question)
    if vision.ok:
        qa_query = build_qa_query(vision, args.question)
        qa = await run_qa_pipeline(settings, qa_query, args.session_id)
    else:
        qa = QAPart(
            ok=False,
            elapsed_ms=0.0,
            query="",
            error_type="VisionFailed",
            error_message=vision.error_message or "Qwen vision did not return usable retrieval hints.",
        )

    return VisionRAGSmokeReport(
        ok=vision.ok and qa.ok,
        image_path=str(image_path),
        image_bytes=len(content),
        mime_type=mimetypes.guess_type(str(image_path))[0] or "image/jpeg",
        session_id=args.session_id,
        vision=vision,
        qa=qa,
    )


def write_report(report: VisionRAGSmokeReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_error_report(exc: Exception, args: argparse.Namespace) -> VisionRAGSmokeReport:
    image_path = Path(args.image).expanduser().resolve()
    image_bytes = image_path.stat().st_size if image_path.exists() and image_path.is_file() else 0
    return VisionRAGSmokeReport(
        ok=False,
        image_path=str(image_path),
        image_bytes=image_bytes,
        mime_type=mimetypes.guess_type(str(image_path))[0] or "",
        session_id=args.session_id,
        vision=VisionPart(
            ok=False,
            provider="qwen",
            model="",
            elapsed_ms=0.0,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
        ),
        qa=QAPart(ok=False, elapsed_ms=0.0),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one controlled Qwen vision to RAG smoke test.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--session-id", default="stage-b3-vision-rag-smoke")
    parser.add_argument("--vision-read-timeout", type=float, default=60.0)
    parser.add_argument("--vision-total-timeout", type=float, default=90.0)
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "eval" / "reports" / "vision_rag_smoke.json"),
    )
    parser.add_argument("--allow-network", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report).expanduser().resolve()
    if not args.allow_network:
        print("Refusing to run real vision-to-RAG smoke without --allow-network. No report was written.")
        return 2
    try:
        report = asyncio.run(run_smoke(args))
    except Exception as exc:
        report = build_error_report(exc, args)
        write_report(report, report_path)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        print(f"Report written to: {report_path}")
        return 1

    write_report(report, report_path)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"Report written to: {report_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
