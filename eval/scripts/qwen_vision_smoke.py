from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402
from app.services.vision.qwen import QwenVisionService  # noqa: E402


DEFAULT_QUESTION = "这张图片可能对应景区哪个位置？请提取可用于景区资料检索的线索。"


@dataclass(slots=True)
class QwenVisionSmokeReport:
    ok: bool
    provider: str
    model: str
    image_path: str
    image_bytes: int
    mime_type: str
    elapsed_ms: float
    scene_summary: str
    detected_text: str
    candidate_attractions: list[str]
    visual_tags: list[str]
    query_hints: list[str]
    retrieval_query: str
    confidence: float
    error_type: str | None = None
    error_message: str | None = None


def load_backend_settings() -> Settings:
    env_file = BACKEND_ROOT / ".env"
    return Settings(_env_file=env_file, _env_file_encoding="utf-8")


def validate_settings(settings: Settings) -> None:
    missing: list[str] = []
    if settings.vision_provider.strip().lower() != "qwen":
        missing.append("VISION_PROVIDER=qwen")
    if not settings.vision_api_key.strip():
        missing.append("VISION_API_KEY")
    if not settings.vision_base_url.strip():
        missing.append("VISION_BASE_URL")
    if not settings.vision_model.strip():
        missing.append("VISION_MODEL")
    if missing:
        raise ValueError(f"Missing or invalid Qwen vision settings: {', '.join(missing)}")


async def run_smoke(image_path: Path, question: str, *, allow_network: bool) -> QwenVisionSmokeReport:
    if not allow_network:
        raise PermissionError("Refusing to call Qwen vision without --allow-network.")
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    settings = load_backend_settings()
    validate_settings(settings)
    content = image_path.read_bytes()
    if len(content) > settings.vision_max_image_bytes:
        raise ValueError(
            f"Image is too large: {len(content)} bytes > {settings.vision_max_image_bytes} bytes"
        )

    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    started_at = perf_counter()
    service = QwenVisionService(settings)
    try:
        result = await service.analyze(
            content,
            filename=image_path.name,
            mime_type=mime_type,
            prompt=question,
        )
    finally:
        await service.aclose()

    elapsed_ms = (perf_counter() - started_at) * 1000
    retrieval_query = result.as_retrieval_query(question)
    provider_error_type = result.raw.get("error_type") if isinstance(result.raw, dict) else None
    provider_error_message = result.raw.get("error_message") if isinstance(result.raw, dict) else None
    has_structured_signal = bool(
        result.scene_summary.strip()
        or result.detected_text.strip()
        or result.candidate_attractions
        or result.visual_tags
        or result.query_hints
    )
    return QwenVisionSmokeReport(
        ok=bool(retrieval_query.strip()) and has_structured_signal and not provider_error_type,
        provider=result.provider,
        model=settings.vision_model,
        image_path=str(image_path),
        image_bytes=len(content),
        mime_type=mime_type,
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


def write_report(report: QwenVisionSmokeReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_error_report(
    exc: Exception,
    *,
    image_path: Path,
    report_path: Path,
) -> QwenVisionSmokeReport:
    report = QwenVisionSmokeReport(
        ok=False,
        provider="qwen",
        model="",
        image_path=str(image_path),
        image_bytes=image_path.stat().st_size if image_path.exists() and image_path.is_file() else 0,
        mime_type=mimetypes.guess_type(str(image_path))[0] or "",
        elapsed_ms=0.0,
        scene_summary="",
        detected_text="",
        candidate_attractions=[],
        visual_tags=[],
        query_hints=[],
        retrieval_query="",
        confidence=0.0,
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    write_report(report, report_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one controlled real Qwen vision smoke test.")
    parser.add_argument("--image", required=True, help="Local image path for the smoke test.")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "eval" / "reports" / "qwen_vision_smoke.json"),
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Required to perform the real Qwen API call.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    if not args.allow_network:
        print("Refusing to call Qwen vision without --allow-network. No report was written.")
        return 2
    if not image_path.exists() or not image_path.is_file():
        print(f"Image file not found: {image_path}. No report was written.")
        return 2
    try:
        report = asyncio.run(
            run_smoke(image_path, args.question, allow_network=args.allow_network)
        )
        write_report(report, report_path)
    except Exception as exc:
        report = build_error_report(exc, image_path=image_path, report_path=report_path)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        print(f"Report written to: {report_path}")
        return 1

    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"Report written to: {report_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
