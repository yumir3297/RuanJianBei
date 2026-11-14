from __future__ import annotations

import hashlib
import json
import os
import platform
import random
from pathlib import Path
from typing import Any, Iterable

LABELS = ["reuse", "distinct", "clarify"]
REASONS = [
    "same_target",
    "cross_object",
    "different_subintent",
    "temporal_conflict",
    "missing_reference",
    "ambiguous_target",
]


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def set_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def count_by(rows: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return counts


def environment_info() -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch

        result.update(
            {
                "torch": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "torch_cuda": torch.version.cuda,
                "cudnn": torch.backends.cudnn.version(),
                "gpu_count": torch.cuda.device_count(),
                "gpus": [
                    {
                        "index": index,
                        "name": torch.cuda.get_device_name(index),
                        "memory_bytes": torch.cuda.get_device_properties(index).total_memory,
                    }
                    for index in range(torch.cuda.device_count())
                ],
            }
        )
    except ImportError:
        result["torch"] = None
    for module_name in ("transformers", "sklearn", "numpy"):
        try:
            module = __import__(module_name)
            result[module_name] = getattr(module, "__version__", "unknown")
        except ImportError:
            result[module_name] = None
    return result


def metrics_from_predictions(
    expected: list[str], predicted: list[str], labels: list[str] | None = None
) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    labels = labels or LABELS
    report = classification_report(
        expected,
        predicted,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    false_reuse_count = sum(
        1 for truth, guess in zip(expected, predicted) if truth != "reuse" and guess == "reuse"
    )
    non_reuse_count = sum(1 for truth in expected if truth != "reuse")
    return {
        "accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, labels=labels, average="macro", zero_division=0),
        "per_class": {label: report[label] for label in labels},
        "confusion_matrix_labels": labels,
        "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        "false_reuse_count": false_reuse_count,
        "false_reuse_denominator": non_reuse_count,
        "false_reuse_rate": false_reuse_count / non_reuse_count if non_reuse_count else 0.0,
    }


def deterministic_guard(row: dict[str, Any]) -> str | None:
    """Return a hard decision when structured facts are conclusive, otherwise None.

    This is deliberately external to the text model. It demonstrates the production
    safety boundary but must not be confused with semantic model performance.
    """

    left = row["left"]
    right = row["right"]
    left_poi, right_poi = left.get("poi_id"), right.get("poi_id")
    left_target, right_target = left.get("target_id"), right.get("target_id")
    if left_poi and right_poi and left_poi != right_poi:
        return "distinct"
    if left_target and right_target and left_target != right_target:
        return "distinct"
    left_date, right_date = left.get("queried_date"), right.get("queried_date")
    if left_date and right_date and left_date != right_date:
        return "distinct"
    return None
