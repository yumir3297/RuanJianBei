#!/usr/bin/env python3
"""GuideMatch 合成数据 train/dev 切分器（cluster 整簇、确定性、零泄漏）。

只读取 ../pairs_train.jsonl，只写入本目录（splits/）。
不生成 synthetic test；同源 dev 不能替代冻结评测集。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SPLIT_DIR = Path(__file__).resolve().parent
DATA_DIR = SPLIT_DIR.parent
SOURCE_PATH = DATA_DIR / "pairs_train.jsonl"

SPLITTER_VERSION = "guidematch-split-v2"
SEED = "guidematch-synthetic-v1-r2"
THRESHOLD = 0.8
TARGET_TOTAL = 135
TARGET_LABEL = {"reuse": 45, "distinct": 45, "clarify": 45}
TARGET_REASON = {
    "same_target": 45,
    "cross_object": 27,
    "different_subintent": 7,
    "temporal_conflict": 11,
    "missing_reference": 36,
    "ambiguous_target": 9,
}
REASON_ORDER = list(TARGET_REASON)
LABEL_ORDER = list(TARGET_LABEL)

NON_TEXT_RE = re.compile(r"[^\u4e00-\u9fffa-z0-9]")


def normalize_text(text: str) -> str:
    return NON_TEXT_RE.sub("", text.lower())


def bigrams(text: str) -> set[str]:
    clean = normalize_text(text)
    if not clean:
        return set()
    if len(clean) == 1:
        return {clean}
    return {clean[i : i + 2] for i in range(len(clean) - 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_left] = root_right


def stable_key(value: str) -> str:
    return hashlib.sha256(f"{SEED}|{value}".encode()).hexdigest()


def objective(
    total: int, labels: Counter[str], reasons: Counter[str]
) -> int:
    """词典序目标的加权实现：总量 > reason > label > 覆盖/下限。"""
    penalty = 10000 * abs(total - TARGET_TOTAL)
    penalty += 10 * sum(abs(reasons[r] - TARGET_REASON[r]) for r in REASON_ORDER)
    penalty += 5 * sum(abs(labels[l] - TARGET_LABEL[l]) for l in LABEL_ORDER)
    penalty += 1000 * sum(1 for r in REASON_ORDER if reasons[r] == 0)
    if reasons["temporal_conflict"] < 9:
        penalty += 2000 * (9 - reasons["temporal_conflict"])
    return penalty


def poi_combo(record: dict[str, Any]) -> str:
    pois = sorted(
        {
            record["left"].get("poi_id"),
            record["right"].get("poi_id"),
        }
        - {None}
    )
    return "|".join(pois) if pois else "none"


def batch_of(record: dict[str, Any]) -> str:
    return record["case_id"].split("-")[2]


def distribution(records: list[dict[str, Any]]) -> dict[str, Counter]:
    return {
        "label": Counter(record["expected"] for record in records),
        "reason": Counter(record["reason"] for record in records),
        "batch": Counter(batch_of(record) for record in records),
        "poi_combo": Counter(poi_combo(record) for record in records),
    }


def main() -> int:
    source_hash_before = sha256_file(SOURCE_PATH)
    records = [
        json.loads(line)
        for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {record["case_id"]: record for record in records}
    ids = [record["case_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise SystemExit("源数据存在重复 case_id")

    texts = {
        record["case_id"]: [bigrams(record["left"]["text"]), bigrams(record["right"]["text"])]
        for record in records
    }

    # 1) record-level union-find：同 family 直接合并。
    uf = UnionFind(ids)
    by_family: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_family[record["family_id"]].append(record["case_id"])
    for members in by_family.values():
        for member in members[1:]:
            uf.union(members[0], member)

    # 2) 任意两记录、任意问句对相似度 >= 0.8 合并。
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if any(
                jaccard(left_bg, right_bg) >= THRESHOLD
                for left_bg in texts[ids[i]]
                for right_bg in texts[ids[j]]
            ):
                uf.union(ids[i], ids[j])

    components: dict[str, list[str]] = defaultdict(list)
    for case_id in ids:
        components[uf.find(case_id)].append(case_id)

    # 3) 稳定 cluster_id：按最小 case_id 排序后编号。
    clusters: list[dict[str, Any]] = []
    for members in sorted((sorted(members) for members in components.values()), key=lambda m: m[0]):
        clusters.append(
            {
                "id": "",
                "members": members,
                "size": len(members),
                "labels": Counter(by_id[case_id]["expected"] for case_id in members),
                "reasons": Counter(by_id[case_id]["reason"] for case_id in members),
            }
        )
    for index, cluster in enumerate(clusters):
        cluster["id"] = f"c{index:04d}"

    # 4) 确定性构造：先用小 cluster，按 reason 配额精确填充。
    remaining = Counter(TARGET_REASON)
    dev_clusters: list[dict[str, Any]] = []
    dev_total = 0

    multi = sorted(
        [cluster for cluster in clusters if cluster["size"] > 1],
        key=lambda cluster: (cluster["size"], stable_key(cluster["id"])),
    )
    single_by_reason: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cluster in clusters:
        if cluster["size"] == 1:
            single_by_reason[next(iter(cluster["reasons"]))].append(cluster)
    for reason in REASON_ORDER:
        single_by_reason[reason].sort(key=lambda cluster: stable_key(cluster["id"]))

    for cluster in multi:
        if cluster["size"] > sum(remaining.values()):
            continue
        if all(cluster["reasons"][reason] <= remaining[reason] for reason in REASON_ORDER):
            dev_clusters.append(cluster)
            dev_total += cluster["size"]
            remaining -= cluster["reasons"]

    for reason in REASON_ORDER:
        for cluster in single_by_reason[reason]:
            if remaining[reason] == 0:
                break
            dev_clusters.append(cluster)
            dev_total += 1
            remaining[reason] -= 1

    if dev_total != TARGET_TOTAL or any(remaining.values()):
        raise SystemExit(f"无法构造精确 dev：total={dev_total}, remaining={dict(remaining)}")

    dev_ids = {case_id for cluster in dev_clusters for case_id in cluster["members"]}
    train_ids = set(ids) - dev_ids

    dev_labels = Counter(by_id[case_id]["expected"] for case_id in dev_ids)
    dev_reasons = Counter(by_id[case_id]["reason"] for case_id in dev_ids)
    base_objective = objective(dev_total, dev_labels, dev_reasons)

    # 5) 局部交换确认：目标已为 0，任何整簇交换都不会更优。
    local_swap_scans = 0
    local_swap_moves = 0
    while True:
        local_swap_scans += 1
        best_delta = 0
        if base_objective == 0:
            break
        # 目标非 0 时的兜底：同尺寸整簇交换。
        dev_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
        train_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for cluster in clusters:
            target = dev_by_size if cluster["members"][0] in dev_ids else train_by_size
            target[cluster["size"]].append(cluster)
        for size in sorted(set(dev_by_size) & set(train_by_size)):
            for dev_cluster in dev_by_size[size]:
                for train_cluster in train_by_size[size]:
                    labels = dev_labels - dev_cluster["labels"] + train_cluster["labels"]
                    reasons = dev_reasons - dev_cluster["reasons"] + train_cluster["reasons"]
                    score = objective(dev_total, labels, reasons)
                    if score < base_objective:
                        best_delta = base_objective - score
                        chosen = (dev_cluster, train_cluster)
        if best_delta == 0:
            break
        dev_cluster, train_cluster = chosen
        dev_clusters.remove(dev_cluster)
        dev_clusters.append(train_cluster)
        dev_ids = {case_id for cluster in dev_clusters for case_id in cluster["members"]}
        train_ids = set(ids) - dev_ids
        dev_labels = dev_labels - dev_cluster["labels"] + train_cluster["labels"]
        dev_reasons = dev_reasons - dev_cluster["reasons"] + train_cluster["reasons"]
        base_objective -= best_delta
        local_swap_moves += 1

    dev_ids = {case_id for cluster in dev_clusters for case_id in cluster["members"]}
    train_ids = set(ids) - dev_ids
    split_of = {case_id: "train" for case_id in train_ids}
    split_of.update({case_id: "dev" for case_id in dev_ids})

    # 6) 写数据文件（保持源记录顺序）。
    train_path = SPLIT_DIR / "train.jsonl"
    dev_path = SPLIT_DIR / "dev.jsonl"
    with train_path.open("w", encoding="utf-8") as handle:
        for record in records:
            if split_of[record["case_id"]] == "train":
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    with dev_path.open("w", encoding="utf-8") as handle:
        for record in records:
            if split_of[record["case_id"]] == "dev":
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    cluster_of = {
        case_id: cluster["id"] for cluster in clusters for case_id in cluster["members"]
    }
    assignments = {
        case_id: {
            "cluster_id": cluster_of[case_id],
            "split": split_of[case_id],
            "family_id": by_id[case_id]["family_id"],
        }
        for case_id in ids
    }
    assignments_path = SPLIT_DIR / "cluster_assignments.json"
    assignments_path.write_text(
        json.dumps(assignments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 7) 全部从磁盘重新读取后再验证。
    def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
        parsed: list[dict[str, Any]] = []
        errors: list[str] = []
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                parsed.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_no}: {exc}")
        return parsed, errors

    train_records, train_json_errors = read_jsonl(train_path)
    dev_records, dev_json_errors = read_jsonl(dev_path)
    assignments_read = json.loads(assignments_path.read_text(encoding="utf-8"))
    json_errors = train_json_errors + dev_json_errors

    train_case_ids = [record["case_id"] for record in train_records]
    dev_case_ids = [record["case_id"] for record in dev_records]
    coverage_ok = (
        len(train_case_ids) == len(set(train_case_ids))
        and len(dev_case_ids) == len(set(dev_case_ids))
        and set(train_case_ids) | set(dev_case_ids) == set(ids)
        and not (set(train_case_ids) & set(dev_case_ids))
    )

    family_train = {record["family_id"] for record in train_records}
    family_dev = {record["family_id"] for record in dev_records}
    cross_family = len(family_train & family_dev)

    cluster_train = {assignments_read[case_id]["cluster_id"] for case_id in train_case_ids}
    cluster_dev = {assignments_read[case_id]["cluster_id"] for case_id in dev_case_ids}
    cross_cluster = len(cluster_train & cluster_dev)

    def normalized_set(rows: list[dict[str, Any]]) -> set[str]:
        return {
            normalize_text(record[side]["text"])
            for record in rows
            for side in ("left", "right")
        }

    exact_cross = len(normalized_set(train_records) & normalized_set(dev_records))

    train_texts = [
        (record["case_id"], record[side]["text"], bigrams(record[side]["text"]))
        for record in train_records
        for side in ("left", "right")
    ]
    dev_texts = [
        (record["case_id"], record[side]["text"], bigrams(record[side]["text"]))
        for record in dev_records
        for side in ("left", "right")
    ]
    near_pairs = 0
    max_sim = 0.0
    max_train_text = ""
    max_dev_text = ""
    for _, train_text, train_bg in train_texts:
        for _, dev_text, dev_bg in dev_texts:
            sim = jaccard(train_bg, dev_bg)
            if sim > max_sim:
                max_sim = sim
                max_train_text = train_text
                max_dev_text = dev_text
            if sim >= THRESHOLD:
                near_pairs += 1

    train_dist = distribution(train_records)
    dev_dist = distribution(dev_records)
    dev_total_read = len(dev_records)
    dev_label_read = dev_dist["label"]
    dev_reason_read = dev_dist["reason"]
    temporal_ok = dev_reason_read["temporal_conflict"] >= 9
    label_floor_ok = all(dev_label_read[label] >= 40 for label in LABEL_ORDER)
    reason_present_ok = all(dev_reason_read[reason] > 0 for reason in REASON_ORDER)

    cluster_sizes = Counter(cluster["size"] for cluster in clusters)
    split_cluster_sizes = {}
    for split, rows in (("train", train_records), ("dev", dev_records)):
        clusters_in_split = Counter(assignments_read[record["case_id"]]["cluster_id"] for record in rows)
        size_counter = Counter()
        seen = set()
        for record in rows:
            cluster_id = assignments_read[record["case_id"]]["cluster_id"]
            if cluster_id in seen:
                continue
            seen.add(cluster_id)
            size_counter[clusters_in_split[cluster_id]] += 1
        split_cluster_sizes[split] = dict(sorted(size_counter.items()))

    source_hash_after = sha256_file(SOURCE_PATH)
    source_unchanged = source_hash_before == source_hash_after

    leakage_zero = (
        coverage_ok
        and cross_family == 0
        and cross_cluster == 0
        and exact_cross == 0
        and near_pairs == 0
    )
    passed = (
        leakage_zero
        and temporal_ok
        and label_floor_ok
        and reason_present_ok
        and source_unchanged
        and not json_errors
        and dev_total_read == TARGET_TOTAL
    )

    actual_deviation = {
        "total": dev_total_read - TARGET_TOTAL,
        "label": {label: dev_label_read[label] - TARGET_LABEL[label] for label in LABEL_ORDER},
        "reason": {
            reason: dev_reason_read[reason] - TARGET_REASON[reason] for reason in REASON_ORDER
        },
    }

    manifest = {
        "source": SOURCE_PATH.name,
        "source_sha256": source_hash_before,
        "splitter_version": SPLITTER_VERSION,
        "splitter_script_sha256": sha256_file(Path(__file__).resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": passed,
        "method": "record-level union-find (family_id + text similarity) + deterministic exact target construction",
        "normalization_rule": "lowercase; remove whitespace and all non [CJK, a-z, 0-9] characters",
        "similarity_metric": "character bigram Jaccard",
        "similarity_threshold": THRESHOLD,
        "seed": SEED,
        "optimization_objective": (
            "lexicographic: exact dev size 135, then min sum|reason-target|, "
            "then min sum|label-45|, then all reasons present and temporal_conflict>=9"
        ),
        "optimization_iterations": local_swap_scans,
        "optimization_detail": {
            "construction_steps": len(dev_clusters),
            "local_swap_scans": local_swap_scans,
            "local_swap_moves": local_swap_moves,
            "final_objective": objective(dev_total_read, dev_label_read, dev_reason_read),
        },
        "case_count": len(records),
        "family_count": len(by_family),
        "cluster_count": len(clusters),
        "cluster_size_distribution": dict(sorted(cluster_sizes.items())),
        "split_case_count": {"train": len(train_records), "dev": len(dev_records)},
        "split_label_distribution": {
            "train": {label: train_dist["label"][label] for label in LABEL_ORDER},
            "dev": {label: dev_label_read[label] for label in LABEL_ORDER},
        },
        "split_reason_distribution": {
            "train": {reason: train_dist["reason"][reason] for reason in REASON_ORDER},
            "dev": {reason: dev_reason_read[reason] for reason in REASON_ORDER},
        },
        "split_batch_distribution": {
            "train": dict(sorted(train_dist["batch"].items())),
            "dev": dict(sorted(dev_dist["batch"].items())),
        },
        "split_poi_combo_distribution": {
            "train": dict(sorted(train_dist["poi_combo"].items())),
            "dev": dict(sorted(dev_dist["poi_combo"].items())),
        },
        "split_cluster_size_distribution": split_cluster_sizes,
        "target_distribution": {
            "total": TARGET_TOTAL,
            "label": TARGET_LABEL,
            "reason": TARGET_REASON,
        },
        "actual_deviation": actual_deviation,
        "leakage": {
            "cross_split_case_count": len(set(train_case_ids) & set(dev_case_ids)),
            "cross_split_family_count": cross_family,
            "cross_split_cluster_count": cross_cluster,
            "cross_split_exact_duplicate_text_count": exact_cross,
            "cross_split_near_duplicate_pair_count": near_pairs,
            "max_cross_split_similarity": round(max_sim, 6),
            "max_similarity_train_text": max_train_text,
            "max_similarity_dev_text": max_dev_text,
            "zero_leakage": leakage_zero,
            "passed": passed,
        },
        "train_sha256": sha256_file(train_path),
        "dev_sha256": sha256_file(dev_path),
        "cluster_assignments_sha256": sha256_file(assignments_path),
        "warnings": [
            "dev 与 train 同源同生成器，只能用于开发期比较，不能证明真实场景泛化。",
            "dev 是按目标分布构造的整簇子集，不是随机抽样，报告指标时需说明选择性偏差。",
            "未生成同源 synthetic test；最终测试必须使用独立冻结评测集。",
            "source 文件在切分前后 SHA-256 保持一致。",
            "所有输出均已从磁盘重新读取并验证。",
        ],
    }
    manifest_path = SPLIT_DIR / "split_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "train": len(train_records),
        "dev": len(dev_records),
        "dev_label": {label: dev_label_read[label] for label in LABEL_ORDER},
        "dev_reason": {reason: dev_reason_read[reason] for reason in REASON_ORDER},
        "max_cross_split_similarity": round(max_sim, 6),
        "passed": passed,
        "deviations": actual_deviation,
        "optimization_iterations": local_swap_scans,
        "local_swap_moves": local_swap_moves,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
