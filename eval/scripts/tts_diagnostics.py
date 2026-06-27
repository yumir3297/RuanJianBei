from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_root in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import Settings  # noqa: E402


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    status_code: int | None
    elapsed_ms: float
    error_type: str | None = None
    error_code: str | None = None
    error_message: str | None = None


async def check_tts(settings: Settings, use_compatible: bool) -> CheckResult:
    name = "compatible" if use_compatible else "native"

    if use_compatible:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/speech"
        payload = {
            "model": settings.tts_model,
            "input": "测试",
            "voice": settings.tts_voice,
            "response_format": "mp3",
        }
    else:
        url = settings.tts_base_url
        payload = {
            "model": settings.tts_model,
            "input": {"text": "测试"},
            "parameters": {
                "voice": settings.tts_voice,
                "format": "mp3",
                "sample_rate": 24000,
            },
        }

    headers = {
        "Authorization": f"Bearer {settings.tts_api_key}",
        "Content-Type": "application/json",
    }

    start = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            elapsed_ms = (perf_counter() - start) * 1000

            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                body_size = len(resp.content)
                return CheckResult(
                    name=name,
                    ok=True,
                    status_code=200,
                    elapsed_ms=elapsed_ms,
                    error_message=f"content_type={content_type[:60]} body_size={body_size}",
                )
            else:
                try:
                    err = resp.json()
                    return CheckResult(
                        name=name,
                        ok=False,
                        status_code=resp.status_code,
                        elapsed_ms=elapsed_ms,
                        error_code=err.get("code", ""),
                        error_message=err.get("message", ""),
                    )
                except ValueError:
                    return CheckResult(
                        name=name,
                        ok=False,
                        status_code=resp.status_code,
                        elapsed_ms=elapsed_ms,
                        error_type="ParseError",
                        error_message=resp.text[:200],
                    )
    except httpx.TimeoutException as exc:
        elapsed_ms = (perf_counter() - start) * 1000
        return CheckResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            error_type="Timeout",
            error_message=str(exc),
        )
    except Exception as exc:
        elapsed_ms = (perf_counter() - start) * 1000
        return CheckResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Required to actually call the TTS API.",
    )
    args = parser.parse_args()

    if not args.allow_network:
        print("Dry run: use --allow-network to make real API calls.")
        return

    settings = Settings()

    if not settings.tts_api_key:
        print("ERROR: TTS_API_KEY is not set in .env")
        return

    print(f"TTS_PROVIDER: {settings.tts_provider}")
    print(f"TTS_MODEL: {settings.tts_model}")
    print(f"TTS_VOICE: {settings.tts_voice}")
    print(f"TTS_API_KEY prefix: {settings.tts_api_key[:10]}...")
    print()

    results = []
    for use_compat in [False, True]:
        print(f"Testing {'compatible' if use_compat else 'native'} endpoint...", end=" ", flush=True)
        result = await check_tts(settings, use_compatible=use_compat)
        print(f"ok={result.ok} status={result.status_code} elapsed={result.elapsed_ms:.0f}ms")
        if result.ok:
            print(f"  body info: {result.error_message}")
        else:
            print(f"  error: code={result.error_code} message={result.error_message}")
        results.append(asdict(result))
        print()

    report_path = PROJECT_ROOT / "eval" / "reports" / "tts_diagnostics_v1.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
