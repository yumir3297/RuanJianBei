from __future__ import annotations

import argparse
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import read_json, root_dir, write_json


def mean_std(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = root_dir()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    run_files = sorted((output / "runs").glob("*/metrics.json"))
    if not run_files:
        raise RuntimeError(f"No completed runs under {output / 'runs'}")

    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    runs: list[dict[str, Any]] = []
    for path in run_files:
        metrics = read_json(path)
        record = {
            "run": path.parent.name,
            "stage": metrics["stage"],
            "seed": metrics["seed"],
            "best_epoch": metrics["best_epoch"],
            "elapsed_seconds": metrics["elapsed_seconds"],
            "trainable_parameters": metrics["parameter_info"]["trainable_parameters"],
            "raw": metrics["dev_metrics"]["raw"],
            "guarded": metrics["dev_metrics"]["guarded"],
        }
        runs.append(record)
        by_stage[record["stage"]].append(record)

    stages: dict[str, Any] = {}
    for stage, records in by_stage.items():
        stages[stage] = {
            "run_count": len(records),
            "raw_macro_f1": mean_std([row["raw"]["macro_f1"] for row in records]),
            "raw_false_reuse_rate": mean_std([row["raw"]["false_reuse_rate"] for row in records]),
            "raw_reuse_precision": mean_std(
                [row["raw"]["per_class"]["reuse"]["precision"] for row in records]
            ),
            "guarded_macro_f1": mean_std([row["guarded"]["macro_f1"] for row in records]),
            "elapsed_seconds": mean_std([row["elapsed_seconds"] for row in records]),
        }

    baseline_path = output / "baseline_tfidf/metrics.json"
    baseline = read_json(baseline_path) if baseline_path.exists() else None
    summary = {
        "boundary": "All train/dev records are synthetic and from one generator. This is not a real-world test.",
        "baseline": baseline,
        "stages": stages,
        "runs": runs,
    }
    write_json(output / "summary.json", summary)

    lines = [
        "# GuideMatch 训练汇总",
        "",
        "> 边界：train/dev 均为同一生成器产生的合成数据；本结果不是独立测试，也不能证明真实游客泛化。",
        "",
        "## 阶段汇总",
        "",
        "| 阶段 | 运行数 | Raw macro-F1 均值±标准差 | Raw 错误复用率 | Raw reuse precision | Guarded macro-F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    if baseline:
        lines.append(
            f"| TF-IDF baseline | 1 | {baseline['macro_f1']:.4f} | "
            f"{baseline['false_reuse_rate']:.4f} | {baseline['per_class']['reuse']['precision']:.4f} | — |"
        )
    for stage, values in stages.items():
        lines.append(
            f"| {stage} | {values['run_count']} | "
            f"{values['raw_macro_f1']['mean']:.4f} ± {values['raw_macro_f1']['std']:.4f} | "
            f"{values['raw_false_reuse_rate']['mean']:.4f} | "
            f"{values['raw_reuse_precision']['mean']:.4f} | "
            f"{values['guarded_macro_f1']['mean']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## 单次运行",
            "",
            "| 运行 | seed | 最佳 epoch | Raw macro-F1 | Raw false-reuse | Guarded macro-F1 | 秒 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in runs:
        lines.append(
            f"| {row['run']} | {row['seed']} | {row['best_epoch']} | "
            f"{row['raw']['macro_f1']:.4f} | {row['raw']['false_reuse_rate']:.4f} | "
            f"{row['guarded']['macro_f1']:.4f} | {row['elapsed_seconds']:.1f} |"
        )
    lines.extend(
        [
            "",
            "完整每类 precision/recall/F1、混淆矩阵和逐条预测见各运行目录。",
            "",
        ]
    )
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Summary written to {output / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
