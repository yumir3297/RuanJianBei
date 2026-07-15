"""
A5 语音端到端延迟分段测量脚本
==============================
用法:
    cd d:\桌面\软件杯
    .\backend\.venv\Scripts\python.exe evaluation\scripts\measure_latency.py

依赖: 后端必须在 http://127.0.0.1:8000 运行
输出: 终端延迟分段报告
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 30

FAQ_QUERIES = [
    "灵山大佛有多高",
    "九龙灌浴每天几点可以看",
    "灵山大佛门票多少钱",
    "灵山胜境开放时间",
    "梵宫里面可以拍照吗",
]

RAG_QUERIES = [
    "灵山大佛像的建造过程是怎样的",
    "梵宫有哪些文化意义和宗教价值",
    "九龙灌浴的佛教典故出自哪部经典",
    "灵山大佛的81级台阶有什么含义",
    "灵山景区有哪些世界之最",
]


@dataclass
class LatencySegment:
    label: str
    values: list[int] = field(default_factory=list)

    @property
    def avg(self) -> float:
        return statistics.mean(self.values) if self.values else 0

    @property
    def p50(self) -> float:
        if not self.values:
            return 0
        s = sorted(self.values)
        return s[int(len(s) * 0.5)]

    @property
    def p95(self) -> float:
        if not self.values:
            return 0
        s = sorted(self.values)
        return s[min(int(len(s) * 0.95), len(s) - 1)]

    @property
    def min_val(self) -> int:
        return min(self.values) if self.values else 0

    @property
    def max_val(self) -> int:
        return max(self.values) if self.values else 0


async def measure_text_chat(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    payload = {
        "query": query,
        "session_id": f"latency-test-{int(time.time() * 1000)}",
        "input_mode": "text",
        "text_only": True,
    }

    result: dict[str, Any] = {
        "full_text": "",
        "sources": [],
        "statuses": [],
        "audio_events": [],
    }
    start = time.perf_counter()
    first_token_time = 0
    audio_received_time = 0

    try:
        async with client.stream(
            "POST", f"{API_BASE}/api/chat/stream",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=10, read=TIMEOUT_SECONDS, write=10, pool=10),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str:
                    continue
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                etype = event.get("type", "")
                edata = event.get("data", {})

                if etype in ("text_chunk", "text") and first_token_time == 0:
                    first_token_time = time.perf_counter()

                if etype == "text_chunk":
                    result["full_text"] += edata.get("token", "")
                elif etype == "text":
                    result["full_text"] = edata.get("text", result["full_text"])
                elif etype == "sources":
                    result["sources"] = edata.get("docs", [])
                elif etype == "status":
                    result["statuses"].append(edata.get("text", ""))
                elif etype == "audio":
                    if audio_received_time == 0:
                        audio_received_time = time.perf_counter()
                    result["audio_events"].append(edata)
                elif etype == "done":
                    break
    except Exception as exc:
        result["_error"] = str(exc)

    total_ms = int((time.perf_counter() - start) * 1000)
    result["_total_ms"] = total_ms
    result["_first_token_ms"] = int((first_token_time - start) * 1000) if first_token_time else 0
    result["_audio_ms"] = int((audio_received_time - start) * 1000) if audio_received_time else 0
    return result


async def main():
    print(f"\n{'='*60}")
    print("A5 语音端到端延迟分段测量")
    print(f"API: {API_BASE}")
    print(f"FAQ 测试: {len(FAQ_QUERIES)} 题  |  RAG 测试: {len(RAG_QUERIES)} 题")
    print(f"{'='*60}\n")

    segments = {
        "faq_total": LatencySegment(label="FAQ 端到端"),
        "faq_ttft": LatencySegment(label="FAQ 首Token"),
        "faq_source": LatencySegment(label="FAQ 来源返回"),
        "rag_total": LatencySegment(label="RAG 端到端"),
        "rag_ttft": LatencySegment(label="RAG 首Token"),
        "rag_source": LatencySegment(label="RAG 来源返回"),
    }

    async with httpx.AsyncClient() as client:
        print("── FAQ 快路径 ──")
        for i, q in enumerate(FAQ_QUERIES, 1):
            print(f"  [{i}/{len(FAQ_QUERIES)}] {q[:40]}...", end=" ", flush=True)
            r = await measure_text_chat(client, q)
            segments["faq_total"].values.append(r["_total_ms"])
            segments["faq_ttft"].values.append(r["_first_token_ms"])
            has_sources = len(r.get("sources", [])) > 0
            print(f"{r['_total_ms']}ms  TTFT={r['_first_token_ms']}ms  src={'Y' if has_sources else 'N'}")

        print("\n── RAG 慢路径 ──")
        for i, q in enumerate(RAG_QUERIES, 1):
            print(f"  [{i}/{len(RAG_QUERIES)}] {q[:40]}...", end=" ", flush=True)
            r = await measure_text_chat(client, q)
            segments["rag_total"].values.append(r["_total_ms"])
            segments["rag_ttft"].values.append(r["_first_token_ms"])
            has_sources = len(r.get("sources", [])) > 0
            print(f"{r['_total_ms']}ms  TTFT={r['_first_token_ms']}ms  src={'Y' if has_sources else 'N'}")

    asr_est = 300
    tts_est = 500

    print(f"\n{'='*60}")
    print("延迟分段报告 (ms)")
    print(f"{'='*60}")
    print(f"{'分段':<20} {'FAQ路径':>10} {'RAG路径':>10} {'说明':>30}")
    print("-" * 70)
    print(f"{'ASR 识别(估)':<20} {asr_est:>10} {asr_est:>10} {'Web Speech API 本地':>30}")
    print(f"{'检索+LLM':<20} {int(segments['faq_total'].avg):>10} {int(segments['rag_total'].avg):>10} {'SSE 收到 done 事件':>30}")
    print(f"{'TTS 合成(估)':<20} {tts_est:>10} {tts_est:>10} {'或 bailian TTS':>30}")
    print(f"{'网络传输(估)':<20} {100:>10} {100:>10} {'预估往返延迟':>30}")
    print("-" * 70)
    faq_e2e = asr_est + int(segments["faq_total"].avg) + tts_est + 100
    rag_e2e = asr_est + int(segments["rag_total"].avg) + tts_est + 100
    print(f"{'端到端合计':<20} {faq_e2e:>10} {rag_e2e:>10} {'ASR+检索+TTS+网络':>30}")

    print(f"\nFAQ 统计: avg={segments['faq_total'].avg:.0f}ms  P50={segments['faq_total'].p50:.0f}ms  P95={segments['faq_total'].p95:.0f}ms")
    print(f"RAG 统计: avg={segments['rag_total'].avg:.0f}ms  P50={segments['rag_total'].p50:.0f}ms  P95={segments['rag_total'].p95:.0f}ms")

    hard_limit = 5000
    print(f"\n赛题要求: 语音端到端 < {hard_limit}ms")
    if faq_e2e < hard_limit and rag_e2e < hard_limit:
        print(f"✅ FAQ={faq_e2e}ms  RAG={rag_e2e}ms  均达标!")
    elif rag_e2e < hard_limit:
        print(f"⚠ FAQ={faq_e2e}ms  RAG={rag_e2e}ms  FAQ 接近上限")
    else:
        print(f"❌ RAG={rag_e2e}ms 超限! 需优化.")


if __name__ == "__main__":
    asyncio.run(main())
