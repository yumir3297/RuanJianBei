from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from package_backend_release import package_backend_release  # noqa: E402


class BackendReleasePackageTests(unittest.TestCase):
    def test_writes_complete_deterministic_candidate_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate.json"
            package_backend_release(
                image_digest="sha256:" + "a" * 64, source_sha="abcdef0123456789", schema_head="head-1",
                capabilities=["visitor-config-v1", "admin-runtime-limits-v1"], output=output,
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
                "format": 1, "image_digest": "sha256:" + "a" * 64,
                "source_sha": "abcdef0123456789", "schema_head": "head-1",
                "capabilities": ["admin-runtime-limits-v1", "visitor-config-v1"],
            })

    def test_rejects_incomplete_metadata_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate.json"
            with self.assertRaises(ValueError):
                package_backend_release(image_digest="sha256:abc", source_sha="abcdef0", schema_head="head", capabilities=["chat"], output=output)
            with self.assertRaises(ValueError):
                package_backend_release(image_digest="sha256:" + "a" * 64, source_sha="abcdef0", schema_head="head", capabilities=[], output=output)
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(ValueError):
                package_backend_release(image_digest="sha256:" + "a" * 64, source_sha="abcdef0", schema_head="head", capabilities=["chat"], output=output)


if __name__ == "__main__":
    unittest.main()
