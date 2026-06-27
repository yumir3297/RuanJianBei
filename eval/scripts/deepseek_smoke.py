from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402


@dataclass(slots=True)
class DeepSeekSmokeReport:
    ok: bool
    provider: str
    model: str
    endpoint: str
    status_code: int | None
    first_token_ms: float | None
    total_ms: float
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    response_preview: str
    error_type: str | None = None
    error_message: str | None = None


def build_chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def parse_stream_payload(payload: str) -> dict[str, Any] | None:
    stripped = payload.strip()
    if not stripped or stripped == "[DONE]":
        return None
    parsed = json.loads(stripped)
    return parsed if isinstance(parsed, dict) else None


async def iter_sse_data(lines: AsyncIterator[str]) -> AsyncIterator[str]:
    async for line in lines:
        if line.startswith("data:"):
            yield line[5:].strip()


def validate_settings(settings: Settings) -> None:
    missing = []
    if settings.llm_provider != "deepseek":
        missing.append("LLM_PROVIDER=deepseek")
    if not settings.llm_api_key.strip():
        missing.append("LLM_API_KEY")
    if not settings.llm_base_url.strip():
        missing.append("LLM_BASE_URL")
    if not settings.llm_model.strip():
        missing.append("LLM_MODEL")
    if missing:
        raise ValueError(f"Missing or invalid DeepSeek settings: {', '.join(missing)}")


async def run_smoke(settings: Settings) -> DeepSeekSmokeReport:
    validate_settings(settings)
    endpoint = build_chat_completions_url(settings.llm_base_url)
    started_at = perf_counter()
    first_token_ms: float | None = None
    status_code: int | None = None
    content_parts: list[str] = []
    finish_reason: str | None = None
    usage: dict[str, Any] = {}

    try:
        timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
        async with asyncio.timeout(45.0):
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.llm_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": "请只回复四个字：连接成功",
                            }
                        ],
                        "stream": True,
                        "stream_options": {"include_usage": True},
                        "temperature": 0,
                        "max_tokens": 32,
                    },
                ) as response:
                    status_code = response.status_code
                    response.raise_for_status()
                    async for payload in iter_sse_data(response.aiter_lines()):
                        if payload == "[DONE]":
                            break
                        chunk = parse_stream_payload(payload)
                        if chunk is None:
                            continue
                        if isinstance(chunk.get("usage"), dict):
                            usage = chunk["usage"]
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        finish_reason = choice.get("finish_reason") or finish_reason
                        delta = choice.get("delta") or {}
                        token = delta.get("content") or ""
                        if token:
                            if first_token_ms is None:
                                first_token_ms = (perf_counter() - started_at) * 1000
                            content_parts.append(str(token))
    except Exception as exc:
        return DeepSeekSmokeReport(
            ok=False,
            provider=settings.llm_provider,
            model=settings.llm_model,
            endpoint=endpoint,
            status_code=status_code,
            first_token_ms=first_token_ms,
            total_ms=(perf_counter() - started_at) * 1000,
            finish_reason=finish_reason,
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            total_tokens=_as_int(usage.get("total_tokens")),
            response_preview="".join(content_parts)[:40],
            error_type=type(exc).__name__,
            error_message=_safe_error_message(exc),
        )

    content = "".join(content_parts).strip()
    return DeepSeekSmokeReport(
        ok=status_code == 200 and bool(content) and first_token_ms is not None,
        provider=settings.llm_provider,
        model=settings.llm_model,
        endpoint=endpoint,
        status_code=status_code,
        first_token_ms=first_token_ms,
        total_ms=(perf_counter() - started_at) * 1000,
        finish_reason=finish_reason,
        prompt_tokens=_as_int(usage.get("prompt_tokens")),
        completion_tokens=_as_int(usage.get("completion_tokens")),
        total_tokens=_as_int(usage.get("total_tokens")),
        response_preview=content[:40],
    )


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) else None


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"DeepSeek returned HTTP {exc.response.status_code}."
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return "DeepSeek request timed out."
    if isinstance(exc, httpx.RequestError):
        return "DeepSeek network request failed."
    return str(exc)[:200]


def main() -> int:
    report = asyncio.run(run_smoke(Settings(_env_file=BACKEND_ROOT / ".env")))
    report_path = PROJECT_ROOT / "eval" / "reports" / "deepseek_smoke_v1.json"
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"report_path={report_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
