from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.scripts.e2e_eval_core import build_dry_run_report, load_cases, write_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an E2E scenic QA testset.")
    parser.add_argument(
        "--testset",
        type=Path,
        default=PROJECT_ROOT / "eval" / "testset" / "e2e_qa_seed.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "eval" / "reports" / "e2e_eval_b2_dry_run.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases(args.testset)
    report = build_dry_run_report(args.testset, cases)
    write_report(report, args.report)
    summary = {
        "valid": report["valid"],
        "case_count": report["case_count"],
        "error_count": len(report["errors"]),
        "category_distribution": report["category_distribution"],
        "behavior_distribution": report["behavior_distribution"],
        "report_path": str(args.report),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if report["errors"]:
        print(json.dumps(report["errors"], ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
