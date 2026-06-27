from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.scripts.e2e_eval_core import (
    build_dry_run_report,
    build_execution_report,
    evaluate_remote_cases,
    load_cases,
    run_async,
    validate_cases,
    write_report,
)  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E2E scenic QA evaluation.")
    parser.add_argument(
        "--testset",
        type=Path,
        default=PROJECT_ROOT / "eval" / "testset" / "e2e_qa_seed.json",
    )
    parser.add_argument(
        "--mode",
        choices=("dry-run", "local-server", "sampled-real"),
        default="dry-run",
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8000/api/chat/stream",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def default_report_path(mode: str) -> Path:
    name = {
        "dry-run": "e2e_eval_b2_dry_run.json",
        "local-server": "e2e_eval_b2_local_server.json",
        "sampled-real": "e2e_eval_b2_sampled_real.json",
    }[mode]
    return PROJECT_ROOT / "eval" / "reports" / name


async def run_remote(args: argparse.Namespace, cases):
    selected_cases = cases
    if args.mode == "sampled-real" and args.limit is None:
        selected_cases = cases[:5]
    elif args.limit is not None:
        selected_cases = cases[: args.limit]

    timeout = httpx.Timeout(
        connect=5.0,
        read=args.timeout_seconds,
        write=10.0,
        pool=5.0,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await evaluate_remote_cases(
            selected_cases,
            endpoint=args.endpoint,
            client=client,
        )


def main() -> int:
    args = parse_args()
    cases = load_cases(args.testset)
    validation_errors = validate_cases(cases)
    report_path = args.report or default_report_path(args.mode)

    if validation_errors:
        report = build_dry_run_report(args.testset, cases)
        write_report(report, report_path)
        print(json.dumps({"valid": False, "errors": validation_errors}, ensure_ascii=False, indent=2))
        return 1

    if args.mode == "dry-run":
        report = build_dry_run_report(args.testset, cases)
        write_report(report, report_path)
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "valid": report["valid"],
                    "case_count": report["case_count"],
                    "report_path": str(report_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not args.allow_network:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Network evaluation requires --allow-network.",
                    "mode": args.mode,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    selected_cases = cases
    if args.mode == "sampled-real" and args.limit is None:
        selected_cases = cases[:5]
    elif args.limit is not None:
        selected_cases = cases[: args.limit]

    results = run_async(run_remote(args, cases))
    report = build_execution_report(
        mode=args.mode,
        testset_path=args.testset,
        cases=selected_cases,
        results=results,
    )
    write_report(report, report_path)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "case_count": report["case_count"],
                "metrics": report["metrics"],
                "failure_count": len(report["failures"]),
                "report_path": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
