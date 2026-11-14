from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import deterministic_guard, read_jsonl  # noqa: E402


class BundleTests(unittest.TestCase):
    def test_split_sizes_and_disjoint_ids(self) -> None:
        train = read_jsonl(ROOT / "data/splits/train.jsonl")
        dev = read_jsonl(ROOT / "data/splits/dev.jsonl")
        self.assertEqual(765, len(train))
        self.assertEqual(135, len(dev))
        self.assertFalse({row["case_id"] for row in train} & {row["case_id"] for row in dev})
        self.assertFalse({row["family_id"] for row in train} & {row["family_id"] for row in dev})

    def test_guard_never_reads_text(self) -> None:
        row = {
            "left": {"text": "arbitrary", "poi_id": "a", "target_id": "x"},
            "right": {"text": "same arbitrary", "poi_id": "b", "target_id": "x"},
        }
        self.assertEqual("distinct", deterministic_guard(row))


if __name__ == "__main__":
    unittest.main()
