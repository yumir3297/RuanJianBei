from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402


@dataclass(slots=True)
class QwenCheckResult:
    name: str
    ok: bool
    status_code: int | None
    elapsed_ms: float
    error_type: str | None = None
    error_message: str | None = None
    body_preview: str = ""
    parsed: dict[str, Any] | None = None


@dataclass(slots=True)
class QwenDiagnosticsReport:
    ok: bool
    provider: str
    base_url: str
    model: str
    api_key_masked: str
    checks: list[QwenCheckResult]
    conclusion: str


def load_backend_settings() -> Settings:
    return Settings(_env_file=BACKEND_ROOT / ".env", _env_file_encoding="utf-8")


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def models_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/models"
    if normalized.endswith("/models"):
        return normalized
    return f"{normalized}/models"


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
    return missing


async def run_get_models(client: httpx.AsyncClient, settings: Settings) -> QwenCheckResult:
    started_at = perf_counter()
    status_code: int | None = None
    try:
        response = await client.get(
            models_url(settings.vision_base_url),
            headers={"Authorization": f"Bearer {settings.vision_api_key}"},
        )
        status_code = response.status_code
        body_preview = response.text[:800]
        parsed: dict[str, Any] | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                data = payload.get("data")
                model_ids = []
                if isinstance(data, list):
                    for item in data[:20]:
                        if isinstance(item, dict) and item.get("id"):
                            model_ids.append(str(item["id"]))
                parsed = {
                    "model_count": len(data) if isinstance(data, list) else None,
                    "first_model_ids": model_ids,
                    "configured_model_listed": settings.vision_model in model_ids,
                }
        except ValueError:
            parsed = None
        return QwenCheckResult(
            name="get_models",
            ok=200 <= response.status_code < 300,
            status_code=status_code,
            elapsed_ms=(perf_counter() - started_at) * 1000,
            body_preview=body_preview,
            parsed=parsed,
        )
    except Exception as exc:
        return QwenCheckResult(
            name="get_models",
            ok=False,
            status_code=status_code,
            elapsed_ms=(perf_counter() - started_at) * 1000,
            error_type=type(exc).__name__,
            error_message=safe_error_message(exc, "Qwen models check"),
        )


async def run_minimal_chat(client: httpx.AsyncClient, settings: Settings) -> QwenCheckResult:
    started_at = perf_counter()
    status_code: int | None = None
    try:
        response = await client.post(
            chat_completions_url(settings.vision_base_url),
            headers={
                "Authorization": f"Bearer {settings.vision_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.vision_model,
                "messages": [{"role": "user", "content": "只回复OK"}],
                "stream": False,
                "temperature": 0,
                "max_tokens": 1,
            },
        )
        status_code = response.status_code
        body_preview = response.text[:800]
        parsed: dict[str, Any] | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = ((payload.get("choices") or [{}])[0].get("message") or {})
                parsed = {
                    "model": payload.get("model"),
                    "content_preview": str(message.get("content") or "")[:40],
                    "usage": payload.get("usage"),
                    "error": payload.get("error"),
                }
        except ValueError:
            parsed = None
        return QwenCheckResult(
            name="minimal_chat",
            ok=200 <= response.status_code < 300,
            status_code=status_code,
            elapsed_ms=(perf_counter() - started_at) * 1000,
            body_preview=body_preview,
            parsed=parsed,
        )
    except Exception as exc:
        return QwenCheckResult(
            name="minimal_chat",
            ok=False,
            status_code=status_code,
            elapsed_ms=(perf_counter() - started_at) * 1000,
            error_type=type(exc).__name__,
            error_message=safe_error_message(exc, "Qwen minimal chat"),
        )


async def run_diagnostics(settings: Settings) -> QwenDiagnosticsReport:
    missing = validate_settings(settings)
    if missing:
        return QwenDiagnosticsReport(
            ok=False,
            provider=settings.vision_provider,
            base_url=settings.vision_base_url,
            model=settings.vision_model,
            api_key_masked=mask_key(settings.vision_api_key),
            checks=[],
            conclusion=f"Missing or invalid settings: {', '.join(missing)}",
        )

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        checks = [
            await run_get_models(client, settings),
            await run_minimal_chat(client, settings),
        ]

    minimal_chat = next(check for check in checks if check.name == "minimal_chat")
    get_models = next(check for check in checks if check.name == "get_models")
    if minimal_chat.ok:
        conclusion = "Qwen compatible chat endpoint, API key, and configured model are usable."
    elif get_models.ok:
        conclusion = "API key and base URL look reachable, but configured model or chat request failed."
    else:
        conclusion = "Qwen API diagnostics failed before a minimal model call succeeded."

    return QwenDiagnosticsReport(
        ok=minimal_chat.ok,
        provider=settings.vision_provider,
        base_url=settings.vision_base_url,
        model=settings.vision_model,
        api_key_masked=mask_key(settings.vision_api_key),
        checks=checks,
        conclusion=conclusion,
    )


def safe_error_message(exc: Exception, prefix: str) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"{prefix} returned HTTP {exc.response.status_code}."
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return f"{prefix} timed out."
    if isinstance(exc, httpx.RequestError):
        return f"{prefix} network request failed."
    return str(exc)[:200]


def write_report(report: QwenDiagnosticsReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Qwen compatible API settings.")
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "eval" / "reports" / "qwen_api_diagnostics.json"),
    )
    parser.add_argument("--allow-network", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.allow_network:
        print("Refusing to diagnose Qwen API without --allow-network. No report was written.")
        return 2

    report_path = Path(args.report).expanduser().resolve()
    report = asyncio.run(run_diagnostics(load_backend_settings()))
    write_report(report, report_path)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"Report written to: {report_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
