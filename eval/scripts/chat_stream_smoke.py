from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class ChatStreamSmokeReport:
    ok: bool
    endpoint: str
    query: str
    status_code: int | None
    first_text_ms: float | None
    total_ms: float
    evidence_ids: list[str] = field(default_factory=list)
    source_titles: list[str] = field(default_factory=list)
    answer: str = ""
    event_types: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


async def iter_sse_events(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, Any]]:
    event_type: str | None = None
    data_lines: list[str] = []
    async for line in lines:
        if not line:
            if event_type and data_lines:
                yield event_type, json.loads("\n".join(data_lines))
            event_type = None
            data_lines = []
            continue
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if event_type and data_lines:
        yield event_type, json.loads("\n".join(data_lines))


async def run_smoke(endpoint: str, query: str) -> ChatStreamSmokeReport:
    started_at = perf_counter()
    status_code: int | None = None
    first_text_ms: float | None = None
    evidence_ids: list[str] = []
    source_titles: list[str] = []
    answer = ""
    event_types: list[str] = []

    try:
        timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                endpoint,
                json={
                    "query": query,
                    "session_id": "stage-b1-real-smoke",
                    "language": "zh-CN",
                },
            ) as response:
                status_code = response.status_code
                response.raise_for_status()
                async for event_type, payload in iter_sse_events(response.aiter_lines()):
                    event_types.append(event_type)
                    if event_type == "sources":
                        for source in payload.get("docs", []):
                            evidence_id = source.get("evidence_id")
                            title = source.get("title")
                            if evidence_id:
                                evidence_ids.append(str(evidence_id))
                            if title:
                                source_titles.append(str(title))
                    elif event_type == "text_chunk" and first_text_ms is None:
                        first_text_ms = (perf_counter() - started_at) * 1000
                    elif event_type == "text":
                        answer = str(payload.get("text") or "")
    except Exception as exc:
        return ChatStreamSmokeReport(
            ok=False,
            endpoint=endpoint,
            query=query,
            status_code=status_code,
            first_text_ms=first_text_ms,
            total_ms=(perf_counter() - started_at) * 1000,
            evidence_ids=evidence_ids,
            source_titles=source_titles,
            answer=answer,
            event_types=event_types,
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )

    ok = (
        status_code == 200
        and bool(answer)
        and bool(evidence_ids)
        and "[证据" in answer
        and "done" in event_types
    )
    return ChatStreamSmokeReport(
        ok=ok,
        endpoint=endpoint,
        query=query,
        status_code=status_code,
        first_text_ms=first_text_ms,
        total_ms=(perf_counter() - started_at) * 1000,
        evidence_ids=evidence_ids,
        source_titles=source_titles,
        answer=answer,
        event_types=event_types,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a UTF-8 SSE chat smoke test.")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8001/api/chat/stream",
    )
    parser.add_argument(
        "--query",
        default="玄奘为什么把马山命名为小灵山？",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = asyncio.run(run_smoke(args.endpoint, args.query))
    report_path = PROJECT_ROOT / "eval" / "reports" / "chat_stream_smoke_b1.json"
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    print(f"report_path={report_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
