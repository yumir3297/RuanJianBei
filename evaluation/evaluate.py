"""
A5 景区导览 AI 数字人 — 100 题端到端评测脚本
==============================================
用法:
    cd d:\桌面\软件杯
    .\backend\.venv\Scripts\python.exe evaluation\evaluate.py

依赖: 后端必须在 http://127.0.0.1:8000 运行
输出: evaluation/eval_report_<timestamp>.json  + 终端摘要
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# ── 配置 ──────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"
QUESTIONS_FILE = Path(__file__).parent / "eval_questions.json"
OUTPUT_DIR = Path(__file__).parent
TIMEOUT_SECONDS = 45

# ── 数据结构 ──────────────────────────────────────────────


@dataclass
class EvalResult:
    question_id: str
    category: str
    query: str
    expected_topic: str = ""
    score: int = 0
    has_sources: bool = False
    source_count: int = 0
    hit_level: str = ""
    latency_ms: int = 0
    answer_preview: str = ""
    error: str = ""
    blind_spot_reject: bool = False  # 盲区题是否正确拒答


@dataclass
class CategorySummary:
    label: str
    total: int
    pass_count: int = 0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    source_rate: float = 0.0  # 有来源的占比


# ── SSE 收集器 ────────────────────────────────────────────


async def collect_sse_stream(client: httpx.AsyncClient, payload: dict) -> dict[str, Any]:
    """收集一次 SSE 聊天流的所有事件，返回聚合结果。"""
    result: dict[str, Any] = {
        "full_text": "",
        "sources": [],
        "statuses": [],
        "hit_level": "",
        "context": None,
    }
    start = time.perf_counter()

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
                if etype == "text_chunk":
                    result["full_text"] += edata.get("token", "")
                elif etype == "text":
                    result["full_text"] = edata.get("text", result["full_text"])
                elif etype == "sources":
                    result["sources"] = edata.get("docs", [])
                elif etype == "status":
                    result["statuses"].append(edata.get("text", ""))
                elif etype == "context":
                    result["context"] = edata
                elif etype == "done":
                    break
    except Exception as exc:
        result["_error"] = str(exc)

    result["_latency_ms"] = int((time.perf_counter() - start) * 1000)
    return result


# ── 评分逻辑 ──────────────────────────────────────────────


def score_answer(query: str, full_text: str, category: str,
                 ground_truth: list[str], reject_keywords: list[str],
                 sources: list[dict]) -> tuple[int, str]:
    """返回 (1-5分, 命中等级)"""
    text = full_text.strip().lower()

    # 知识盲区题：应当拒答
    if category == "blind_spot":
        if reject_keywords:
            if any(kw.lower() in text for kw in reject_keywords):
                return (5, "blind_spot_correct_reject")
        if len(text) < 20 or "没有" in text or "暂时" in text or "不足" in text or "无法" in text:
            return (5, "blind_spot_correct_reject")
        if len(text) > 300:  # 瞎编了
            return (1, "blind_spot_hallucination")
        return (4, "blind_spot_likely_reject")

    # 常规题
    if not text:
        return (1, "empty")

    # 无来源 → 最多 2 分
    if not sources:
        if any(kw.lower() in text for kw in ["没有资料", "暂时无法", "资料不足", "没有足够"]):
            return (2, "no_evidence_honest")
        return (1, "no_sources")

    hits = 0
    for kw in ground_truth:
        if kw.lower() in text:
            hits += 1

    has_sources = len(sources) > 0

    if not ground_truth:
        # 无标准答案的开放题，有来源就给 4 分
        return (4, "open_with_sources") if has_sources else (2, "open_no_sources")

    ratio = hits / len(ground_truth) if ground_truth else 0
    if ratio >= 0.8:
        return (5, "exact_match")
    elif ratio >= 0.5:
        return (4, "partial_match")
    elif ratio >= 0.2:
        return (3, "some_match")
    elif has_sources:
        return (2, "weak_match_with_sources")
    else:
        return (1, "no_match")


def detect_hit_level(statuses: list[str], sources: list[dict], full_text: str) -> str:
    """从 SSE 状态推断命中层级。"""
    status_text = " ".join(statuses).lower()
    if "faq" in status_text:
        return "faq"
    if "缓存" in status_text or "cache" in status_text:
        return "cache"
    if sources:
        if len(full_text) > 300:
            return "rag_llm"
        return "rag_evidence"
    if "没有" in full_text or "不足" in full_text:
        return "rag_insufficient"
    return "unknown"


# ── 主评测 ────────────────────────────────────────────────


async def main():
    questions_path = QUESTIONS_FILE
    if not questions_path.exists():
        print(f"[ERROR] 找不到题目文件: {questions_path}")
        sys.exit(1)

    with open(questions_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    all_questions = dataset["questions"]
    categories_meta = {c["key"]: c for c in dataset["categories"]}

    print(f"\n{'='*60}")
    print(f"A5 景区导览 AI 数字人 — 100 题端到端评测")
    print(f"API: {API_BASE}")
    print(f"题目总数: {len(all_questions)}")
    print(f"超时: {TIMEOUT_SECONDS}s / 题")
    print(f"{'='*60}\n")

    results: list[EvalResult] = []

    async with httpx.AsyncClient() as client:
        for idx, q in enumerate(all_questions, 1):
            qid = q["id"]
            category = q["category"]
            cat_label = categories_meta.get(category, {}).get("label", category)

            print(f"[{idx:03d}/100] {qid} ({cat_label}): {q['query'][:50]}...", end=" ", flush=True)

            payload = {
                "query": q["query"],
                "session_id": f"eval-{qid}",
                "input_mode": "text",
                "text_only": True,
            }

            collected = await collect_sse_stream(client, payload)

            err = collected.get("_error", "")
            full_text = collected.get("full_text", "")
            sources = collected.get("sources", [])
            statuses = collected.get("statuses", [])

            score_val, reason = score_answer(
                q["query"], full_text, category,
                q.get("ground_truth", []), q.get("reject_keywords", []), sources,
            )

            hit_level = detect_hit_level(statuses, sources, full_text)
            if err and not full_text:
                hit_level = "error"

            result = EvalResult(
                question_id=qid,
                category=category,
                query=q["query"],
                expected_topic=q.get("expected_topic", ""),
                score=score_val,
                has_sources=len(sources) > 0,
                source_count=len(sources),
                hit_level=hit_level,
                latency_ms=collected.get("_latency_ms", 0),
                answer_preview=full_text[:100],
                error=err,
                blind_spot_reject=(category == "blind_spot" and score_val >= 4),
            )
            results.append(result)

            icon = {5: "★", 4: "●", 3: "◐", 2: "○", 1: "✗"}.get(score_val, "?")
            print(f"{icon} {score_val}/5  {result.latency_ms}ms  [{reason}]")

    # ── 汇总 ──
    print(f"\n{'='*60}")
    print("评测完成 — 汇总")
    print(f"{'='*60}")

    # 按类别汇总
    category_summaries: dict[str, CategorySummary] = {}
    for c in dataset["categories"]:
        category_summaries[c["key"]] = CategorySummary(label=c["label"], total=0)

    for r in results:
        cat = category_summaries.get(r.category)
        if cat is None:
            cat = CategorySummary(label=r.category, total=0)
            category_summaries[r.category] = cat
        cat.total += 1
        if r.score >= 3:
            cat.pass_count += 1
        cat.avg_score += r.score
        cat.avg_latency_ms += r.latency_ms
        if r.has_sources:
            cat.source_rate += 1

    for key, cat in category_summaries.items():
        if cat.total > 0:
            cat.avg_score /= cat.total
            cat.avg_latency_ms /= cat.total
            cat.source_rate = cat.source_rate / cat.total * 100

    print(f"\n{'类别':<20} {'题数':>4} {'通过(≥3)':>10} {'通过率':>8} {'均分':>6} {'均延迟':>8} {'来源率':>8}")
    print("-" * 70)
    for key, cat in category_summaries.items():
        if cat.total == 0:
            continue
        rate = cat.pass_count / cat.total * 100
        print(f"{cat.label:<20} {cat.total:>4} {cat.pass_count:>8}/{cat.total} {rate:>6.1f}% {cat.avg_score:>5.2f} {cat.avg_latency_ms:>7.0f}ms {cat.source_rate:>6.1f}%")

    # 总览
    total = len(results)
    total_pass = sum(1 for r in results if r.score >= 3)
    total_score = sum(r.score for r in results)
    total_latency = sum(r.latency_ms for r in results)
    total_source = sum(1 for r in results if r.has_sources)
    blind_correct = sum(1 for r in results if r.blind_spot_reject)

    print("-" * 70)
    print(f"{'总计':<20} {total:>4} {total_pass:>8}/{total} {total_pass/total*100:>6.1f}% {total_score/total:>5.2f} {total_latency/total:>7.0f}ms {total_source/total*100:>6.1f}%")

    print(f"\n准确率(≥3分) = {total_pass}/{total} = {total_pass/total*100:.1f}%")
    print(f"平均分 = {total_score/total:.2f}/5")
    print(f"平均延迟 = {total_latency/total:.0f}ms  |  P50 = {p50_latency(results):.0f}ms  |  P95 = {p95_latency(results):.0f}ms")
    print(f"来源展示率 = {total_source}/{total} = {total_source/total*100:.1f}%")
    if blind_correct > 0:
        blind_total = sum(1 for r in results if r.category == "blind_spot")
        print(f"盲区正确拒答率 = {blind_correct}/{blind_total} = {blind_correct/blind_total*100:.1f}%")

    # ── 失败题列表 ──
    failed = [r for r in results if r.score < 3]
    if failed:
        print(f"\n⚠ 未达标题目 ({len(failed)} 题，得分 < 3):")
        for r in failed:
            print(f"  [{r.question_id}] 得分={r.score}/5  {r.query[:60]}")
            if r.error:
                print(f"         错误: {r.error}")
            if r.answer_preview:
                print(f"         回答: {r.answer_preview}...")

    # ── 输出 JSON 报告 ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"eval_report_{timestamp}.json"

    report = {
        "meta": {
            "title": "A5 100题端到端评测报告",
            "timestamp": timestamp,
            "total_questions": total,
            "pass_count": total_pass,
            "pass_rate": round(total_pass / total * 100, 1) if total > 0 else 0,
            "avg_score": round(total_score / total, 2) if total > 0 else 0,
            "avg_latency_ms": round(total_latency / total, 0) if total > 0 else 0,
            "p50_latency_ms": p50_latency(results),
            "p95_latency_ms": p95_latency(results),
            "source_display_rate": round(total_source / total * 100, 1) if total > 0 else 0,
        },
        "by_category": {
            key: {
                "label": cat.label,
                "total": cat.total,
                "pass_count": cat.pass_count,
                "pass_rate": round(cat.pass_count / cat.total * 100, 1) if cat.total > 0 else 0,
                "avg_score": round(cat.avg_score, 2),
                "avg_latency_ms": round(cat.avg_latency_ms, 0),
                "source_rate": round(cat.source_rate, 1),
            }
            for key, cat in category_summaries.items()
            if cat.total > 0
        },
        "details": [
            {
                "id": r.question_id,
                "category": r.category,
                "query": r.query,
                "expected_topic": r.expected_topic,
                "score": r.score,
                "has_sources": r.has_sources,
                "source_count": r.source_count,
                "hit_level": r.hit_level,
                "latency_ms": r.latency_ms,
                "answer_preview": r.answer_preview,
                "error": r.error,
                "blind_spot_reject": r.blind_spot_reject,
            }
            for r in results
        ],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 详细报告已保存: {report_path}")

    # 结论
    if total_pass / total >= 0.9:
        print("\n✅ 通过验收阈值 (≥90%)!")
    elif total_pass / total >= 0.75:
        print("\n⚠ 接近阈值，建议排查失败题。")
    else:
        print("\n❌ 未达到 90% 准确率目标，需修复。")

    return report


def p50_latency(results: list[EvalResult]) -> int:
    sorted_vals = sorted(r.latency_ms for r in results if r.latency_ms > 0)
    if not sorted_vals:
        return 0
    idx = int(len(sorted_vals) * 0.5)
    return sorted_vals[idx]


def p95_latency(results: list[EvalResult]) -> int:
    sorted_vals = sorted(r.latency_ms for r in results if r.latency_ms > 0)
    if not sorted_vals:
        return 0
    idx = int(len(sorted_vals) * 0.95)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


if __name__ == "__main__":
    asyncio.run(main())
