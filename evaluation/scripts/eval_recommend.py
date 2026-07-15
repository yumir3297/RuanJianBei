"""
A5 路线推荐个性化程度量化评测脚本
==================================
用法:
    cd d:\桌面\软件杯
    .\backend\.venv\Scripts\python.exe evaluation\scripts\eval_recommend.py

依赖: 后端必须在 http://127.0.0.1:8000 运行
输出: 终端评测报告
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000"

EXPECTED_ROUTES = {
    "route_001": "历史文化爱好者路线",
    "route_002": "自然风光爱好者路线",
    "route_003": "亲子家庭路线",
}

TEST_CASES = [
    {
        "label": "亲子家庭",
        "payload": {
            "session_id": "eval-recommend-family",
            "interests": ["亲子", "轻松", "互动"],
            "audience_type": "family",
            "available_hours": 4,
            "avoid_crowded": False,
        },
        "expected_route_id": "route_003",
    },
    {
        "label": "文化爱好者",
        "payload": {
            "session_id": "eval-recommend-culture",
            "interests": ["历史", "文化", "佛教"],
            "audience_type": "culture",
            "available_hours": 6,
            "avoid_crowded": False,
        },
        "expected_route_id": "route_001",
    },
    {
        "label": "自然风光摄影",
        "payload": {
            "session_id": "eval-recommend-nature",
            "interests": ["自然", "风光", "摄影"],
            "audience_type": "leisure",
            "available_hours": 5,
            "avoid_crowded": False,
        },
        "expected_route_id": "route_002",
    },
    {
        "label": "自由背包客",
        "payload": {
            "session_id": "eval-recommend-free",
            "interests": ["探索", "自由"],
            "audience_type": "free",
            "available_hours": 8,
            "avoid_crowded": False,
        },
        "expected_route_id": "route_001",
    },
    {
        "label": "老年团(文化偏好)",
        "payload": {
            "session_id": "eval-recommend-elder",
            "interests": ["轻松", "平坦", "文化"],
            "audience_type": "general",
            "available_hours": 3,
            "avoid_crowded": True,
        },
        "expected_route_id": "route_001",
    },
    {
        "label": "亲子(含关键词'孩子')",
        "payload": {
            "session_id": "eval-recommend-child",
            "interests": ["孩子", "寓教于乐"],
            "audience_type": "general",
            "available_hours": 4,
            "avoid_crowded": False,
        },
        "expected_route_id": "route_003",
    },
]


@dataclass
class RecommendResult:
    label: str
    expected_id: str
    actual_id: str = ""
    actual_title: str = ""
    match: bool = False
    route_count: int = 0
    error: str = ""


async def call_recommend(client: httpx.AsyncClient, payload: dict) -> dict[str, Any]:
    try:
        response = await client.post(
            f"{API_BASE}/api/recommend/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=10, read=15, write=10, pool=10),
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"_error": str(exc)}


async def main():
    print(f"\n{'='*60}")
    print("A5 路线推荐个性化程度量化评测")
    print(f"API: {API_BASE}")
    print(f"测试用例: {len(TEST_CASES)} 个")
    print(f"{'='*60}\n")

    results: list[RecommendResult] = []

    async with httpx.AsyncClient() as client:
        for i, tc in enumerate(TEST_CASES, 1):
            print(f"[{i}/{len(TEST_CASES)}] {tc['label']}...", end=" ", flush=True)

            data = await call_recommend(client, tc["payload"])
            err = data.get("_error", "")

            if err:
                r = RecommendResult(
                    label=tc["label"],
                    expected_id=tc["expected_route_id"],
                    error=err,
                )
                print(f"❌ 错误: {err}")
            else:
                routes = data.get("routes", [])
                primary = routes[0] if routes else {}
                actual_id = primary.get("route_id", "none")
                r = RecommendResult(
                    label=tc["label"],
                    expected_id=tc["expected_route_id"],
                    actual_id=actual_id,
                    actual_title=primary.get("title", ""),
                    match=(actual_id == tc["expected_route_id"]),
                    route_count=len(routes),
                )
                status = "✅" if r.match else "❌"
                print(f"{status}  返回: {r.actual_id} ({EXPECTED_ROUTES.get(r.actual_id, r.actual_title)})  routes={r.route_count}")

            results.append(r)

    total = len(results)
    correct = sum(1 for r in results if r.match)
    errors = [r for r in results if r.error]

    print(f"\n{'='*60}")
    print("评测汇总")
    print(f"{'='*60}")
    print(f"总测试数:       {total}")
    print(f"正确匹配:       {correct}/{total} = {correct/total*100:.1f}%")
    if errors:
        print(f"错误数:         {len(errors)}")
        for r in errors:
            print(f"  - {r.label}: {r.error}")

    failed = [r for r in results if not r.match and not r.error]
    if failed:
        print(f"\n⚠ 路线不匹配 ({len(failed)} 个):")
        for r in failed:
            expected_name = EXPECTED_ROUTES.get(r.expected_id, r.expected_id)
            actual_name = EXPECTED_ROUTES.get(r.actual_id, r.actual_id)
            print(f"  {r.label} → 期望: {r.expected_id}({expected_name})  实际: {r.actual_id}({actual_name})")

    if correct == total:
        print("\n✅ 所有路线推荐符合预期!")
    elif correct / total >= 0.8:
        print(f"\n⚠ 部分不匹配 ({correct}/{total})，可接受范围为演示。")
    else:
        print(f"\n❌ 匹配率过低 ({correct}/{total})，需检查推荐引擎匹配逻辑。")


if __name__ == "__main__":
    asyncio.run(main())
