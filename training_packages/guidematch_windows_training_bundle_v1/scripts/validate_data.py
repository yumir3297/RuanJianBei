from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import LABELS, REASONS, count_by, read_jsonl, root_dir, sha256_file, write_json


REQUIRED_ROW_KEYS = {"case_id", "family_id", "left", "right", "expected", "reason", "origin"}
REQUIRED_SIDE_KEYS = {"text"}


def validate_rows(rows: list[dict[str, Any]], split: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        location = f"{split}:{index}"
        missing = REQUIRED_ROW_KEYS - row.keys()
        if missing:
            errors.append(f"{location}: missing keys {sorted(missing)}")
            continue
        if row["case_id"] in seen:
            errors.append(f"{location}: duplicate case_id {row['case_id']}")
        seen.add(row["case_id"])
        if row["expected"] not in LABELS:
            errors.append(f"{location}: invalid expected {row['expected']}")
        if row["reason"] not in REASONS:
            errors.append(f"{location}: invalid reason {row['reason']}")
        for side_name in ("left", "right"):
            side = row[side_name]
            side_missing = REQUIRED_SIDE_KEYS - side.keys()
            if side_missing:
                errors.append(f"{location}.{side_name}: missing keys {sorted(side_missing)}")
            if not isinstance(side.get("text"), str) or not side.get("text", "").strip():
                errors.append(f"{location}.{side_name}: empty text")
            for optional_key in ("poi_id", "target_id"):
                if optional_key in side and not isinstance(side[optional_key], str):
                    errors.append(f"{location}.{side_name}: {optional_key} must be a string when present")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/data_validation.json"))
    args = parser.parse_args()
    root = root_dir()
    train_path = root / "data/splits/train.jsonl"
    dev_path = root / "data/splits/dev.jsonl"
    train = read_jsonl(train_path)
    dev = read_jsonl(dev_path)
    errors = validate_rows(train, "train") + validate_rows(dev, "dev")

    train_ids = {row["case_id"] for row in train}
    dev_ids = {row["case_id"] for row in dev}
    train_families = {row["family_id"] for row in train}
    dev_families = {row["family_id"] for row in dev}
    case_overlap = sorted(train_ids & dev_ids)
    family_overlap = sorted(train_families & dev_families)
    if case_overlap:
        errors.append(f"case overlap: {case_overlap[:10]}")
    if family_overlap:
        errors.append(f"family overlap: {family_overlap[:10]}")
    if len(train) != 765:
        errors.append(f"expected 765 train rows, got {len(train)}")
    if len(dev) != 135:
        errors.append(f"expected 135 dev rows, got {len(dev)}")

    result = {
        "passed": not errors,
        "errors": errors,
        "train": {
            "count": len(train),
            "labels": count_by(train, "expected"),
            "reasons": count_by(train, "reason"),
            "sha256": sha256_file(train_path),
        },
        "dev": {
            "count": len(dev),
            "labels": count_by(dev, "expected"),
            "reasons": count_by(dev, "reason"),
            "sha256": sha256_file(dev_path),
        },
        "case_overlap_count": len(case_overlap),
        "family_overlap_count": len(family_overlap),
        "warning": "Both splits are synthetic and share one generator; dev is not a real-world test set.",
    }
    output = args.output if args.output.is_absolute() else root / args.output
    write_json(output, result)
    print(f"Data validation {'passed' if result['passed'] else 'FAILED'}: {output}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
