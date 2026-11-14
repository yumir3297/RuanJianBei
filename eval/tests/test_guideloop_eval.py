import json
import tempfile
import unittest
from pathlib import Path

from eval.scripts.guideloop_eval import validate_fixtures


class GuideLoopFixtureContractTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / "fixtures" / "guideloop"
        self.manifest = json.loads((self.root / "manifest.json").read_text())

    def test_duplicate_pair_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
                (root / name).write_bytes((self.root / name).read_bytes())
            rows = (root / "pairs_test.jsonl").read_text().splitlines()
            duplicate = json.loads(rows[0])
            duplicate["case_id"] = json.loads((root / "pairs_dev.jsonl").read_text().splitlines()[0])["case_id"]
            rows[0] = json.dumps(duplicate, ensure_ascii=False)
            (root / "pairs_test.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                validate_fixtures(root)

    def test_missing_expected_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
                (root / name).write_bytes((self.root / name).read_bytes())
            rows = (root / "pairs_dev.jsonl").read_text().splitlines()
            row = json.loads(rows[0])
            row.pop("expected")
            rows[0] = json.dumps(row, ensure_ascii=False)
            (root / "pairs_dev.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "expected"):
                validate_fixtures(root)

    def test_family_leakage_between_splits_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
                (root / name).write_bytes((self.root / name).read_bytes())
            dev_family = json.loads((root / "pairs_dev.jsonl").read_text().splitlines()[0])["family_id"]
            rows = (root / "pairs_test.jsonl").read_text().splitlines()
            row = json.loads(rows[0])
            row["family_id"] = dev_family
            rows[0] = json.dumps(row, ensure_ascii=False)
            (root / "pairs_test.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "family"):
                validate_fixtures(root)

    def test_hard_negative_without_object_or_time_constraint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
                (root / name).write_bytes((self.root / name).read_bytes())
            rows = (root / "pairs_test.jsonl").read_text().splitlines()
            row = next(json.loads(line) for line in rows if json.loads(line)["reason"] == "cross_object")
            row["left"]["target_id"] = None
            row["right"]["target_id"] = None
            row["left"]["poi_id"] = None
            row["right"]["poi_id"] = None
            rows = [json.dumps(row, ensure_ascii=False) if json.loads(line)["case_id"] == row["case_id"] else line for line in rows]
            (root / "pairs_test.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "poi_id"):
                validate_fixtures(root)

    def test_synthetic_notice_without_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
                (root / name).write_bytes((self.root / name).read_bytes())
            notices = json.loads((root / "notices.json").read_text())
            notices[0].pop("origin")
            (root / "notices.json").write_text(json.dumps(notices, ensure_ascii=False, indent=2))
            with self.assertRaisesRegex(ValueError, "origin"):
                validate_fixtures(root)

    def test_question_texts_do_not_leak_between_pair_splits(self):
        dev = [json.loads(line) for line in (self.root / "pairs_dev.jsonl").read_text().splitlines()]
        test = [json.loads(line) for line in (self.root / "pairs_test.jsonl").read_text().splitlines()]
        dev_texts = {side["text"] for row in dev for side in (row["left"], row["right"])}
        test_texts = {side["text"] for row in test for side in (row["left"], row["right"])}
        self.assertFalse(dev_texts & test_texts, sorted(dev_texts & test_texts))

    def test_frozen_corpus_has_exact_sizes_and_family_isolation(self):
        report = validate_fixtures(self.root)
        self.assertEqual(report["pairs_dev"], 20)
        self.assertEqual(report["pairs_test"], 40)
        self.assertEqual(report["replay"], 18)
        self.assertEqual(report["test_expected"], {"reuse": 20, "distinct": 12, "clarify": 8})

    def test_temporal_replay_forbids_concrete_superseded_claims(self):
        replay = [json.loads(line) for line in (self.root / "replay.jsonl").read_text().splitlines()]
        by_id = {row["case_id"]: row["expected"]["forbidden_claims"] for row in replay}
        self.assertIn("2026-11-10 14:30", by_id["replay-V1-date-control"])
        self.assertIn("2026-11-10 14:00", by_id["replay-V2-date-control"])
        self.assertIn("2026-11-10 14:00", by_id["replay-v3-05"])
        self.assertIn("2026-11-10 14:30", by_id["replay-v3-05"])
