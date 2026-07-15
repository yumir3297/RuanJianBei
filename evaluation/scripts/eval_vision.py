"""
A5 Vision 图片识别链路准确率评测脚本
====================================
用法:
    cd d:\桌面\软件杯
    .\backend\.venv\Scripts\python.exe evaluation\scripts\eval_vision.py

依赖: 后端必须在 http://127.0.0.1:8000 运行
输入: frontend/public/assets/slides/ 中的景点图片
输出: 终端准确率报告
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000"
SLIDES_DIR = Path(__file__).parent.parent.parent / "frontend" / "public" / "assets" / "slides"

TEST_CASES = [
    {"file": "灵山大佛.png", "ground_truth": "灵山大佛", "mime": "image/png"},
    {"file": "灵山梵宫.png", "ground_truth": "灵山梵宫", "mime": "image/png"},
    {"file": "九龙灌浴.png", "ground_truth": "九龙灌浴", "mime": "image/png"},
    {"file": "五印坛城.png", "ground_truth": "五印坛城", "mime": "image/png"},
    {"file": "祥符禅寺.png", "ground_truth": "祥符禅寺", "mime": "image/png"},
    {"file": "灵山大照壁.png", "ground_truth": "灵山大照壁", "mime": "image/png"},
    {"file": "百子戏弥勒.png", "ground_truth": "百子戏弥勒", "mime": "image/png"},
    {"file": "降魔浮雕.png", "ground_truth": "降魔浮雕", "mime": "image/png"},
    {"file": "阿育王柱_1.png", "ground_truth": "阿育王柱", "mime": "image/png"},
    {"file": "曼飞龙塔.png", "ground_truth": "曼飞龙塔", "mime": "image/png"},
]


@dataclass
class VisionEvalResult:
    file: str
    ground_truth: str
    top1_match: bool = False
    top3_recall: bool = False
    candidates: list[str] = field(default_factory=list)
    scene_summary: str = ""
    confidence: float = 0.0
    latency_ms: int = 0
    error: str = ""


async def analyze_image(client: httpx.AsyncClient, file_path: Path, mime: str) -> dict[str, Any]:
    content = file_path.read_bytes()
    filename = file_path.name
    start = time.perf_counter()

    try:
        response = await client.post(
            f"{API_BASE}/api/vision/analyze",
            content=content,
            headers={"Content-Type": mime},
            params={"filename": filename, "question": "这张景区图片对应哪个景点？请给出准确名称。"},
            timeout=httpx.Timeout(connect=10, read=45, write=15, pool=10),
        )
        response.raise_for_status()
        data = response.json()
        data["_latency_ms"] = int((time.perf_counter() - start) * 1000)
        return data
    except Exception as exc:
        return {
            "_error": str(exc),
            "_latency_ms": int((time.perf_counter() - start) * 1000),
        }


def check_match(candidates: list[str], ground_truth: str) -> tuple[bool, bool]:
    if not candidates:
        return (False, False)
    gt = ground_truth.lower()
    normalized_candidates = [c.strip().lower() for c in candidates]
    top1 = gt in normalized_candidates[0] or normalized_candidates[0] in gt
    top3 = any(gt in c or c in gt for c in normalized_candidates[:3])
    return (top1, top3)


async def main():
    print(f"\n{'='*60}")
    print("A5 Vision 图片识别链路准确率评测")
    print(f"API: {API_BASE}")
    print(f"测试图片: {len(TEST_CASES)} 张")
    print(f"{'='*60}\n")

    results: list[VisionEvalResult] = []
    missing_files = []

    for tc in TEST_CASES:
        file_path = SLIDES_DIR / tc["file"]
        if not file_path.exists():
            missing_files.append(tc["file"])
            continue
        tc["_path"] = file_path

    if missing_files:
        print(f"⚠ 缺失文件 ({len(missing_files)}): {missing_files}")
        if not any("_path" in tc for tc in TEST_CASES):
            print("无可用测试图片，请确认 slides 目录存在。")
            return

    async with httpx.AsyncClient() as client:
        for i, tc in enumerate(TEST_CASES, 1):
            file_path = tc.get("_path")
            if not file_path:
                continue

            print(f"[{i}/{len(TEST_CASES)}] {tc['file']}...", end=" ", flush=True)

            data = await analyze_image(client, file_path, tc["mime"])

            err = data.get("_error", "")
            candidates = data.get("candidate_attractions", [])
            top1, top3 = check_match(candidates, tc["ground_truth"])

            result = VisionEvalResult(
                file=tc["file"],
                ground_truth=tc["ground_truth"],
                top1_match=top1,
                top3_recall=top3,
                candidates=candidates,
                scene_summary=data.get("scene_summary", ""),
                confidence=data.get("confidence", 0),
                latency_ms=data.get("_latency_ms", 0),
                error=err,
            )
            results.append(result)

            status = "✅" if top1 else ("🟡" if top3 else "❌")
            print(f"{status}  Top1={'Y' if top1 else 'N'}  Top3={'Y' if top3 else 'N'}  conf={result.confidence:.0%}  {result.latency_ms}ms")
            if candidates:
                print(f"      候选: {candidates[:5]}")

    if not results:
        print("\n无有效结果。")
        return

    total = len(results)
    top1_correct = sum(1 for r in results if r.top1_match)
    top3_correct = sum(1 for r in results if r.top3_recall)
    avg_confidence = statistics.mean(r.confidence for r in results)
    avg_latency = statistics.mean(r.latency_ms for r in results)
    errors = [r for r in results if r.error]

    print(f"\n{'='*60}")
    print("评测汇总")
    print(f"{'='*60}")
    print(f"总测试数:       {total}")
    print(f"Top-1 准确率:   {top1_correct}/{total} = {top1_correct/total*100:.1f}%")
    print(f"Top-3 召回率:   {top3_correct}/{total} = {top3_correct/total*100:.1f}%")
    print(f"平均置信度:     {avg_confidence:.1%}")
    print(f"平均延迟:       {avg_latency:.0f}ms")
    if errors:
        print(f"错误数:         {len(errors)}")
        for r in errors:
            print(f"  - {r.file}: {r.error}")

    failed = [r for r in results if not r.top3_recall]
    if failed:
        print(f"\n⚠ 识别失败 ({len(failed)} 张):")
        for r in failed:
            print(f"  {r.file} → 期望: {r.ground_truth}  候选: {r.candidates}")


if __name__ == "__main__":
    asyncio.run(main())
