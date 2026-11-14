from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_release_compatibility import (  # noqa: E402
    CompatibilityError,
    check_backend_upgrade,
    check_frontend_release,
)
from package_frontend_release import CAPABILITIES  # noqa: E402


def write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class ReleaseCompatibilityTests(unittest.TestCase):
    def test_tourist_package_requires_cass_guide_context_capability(self):
        self.assertIn("guide-context-v1", CAPABILITIES["tourist"])

    def test_missing_backend_metadata_rejects_frontend_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = write(root / "frontend.json", {"required_backend_capabilities": ["visitor-config-v1"]})
            with self.assertRaises(CompatibilityError):
                check_frontend_release(release, root / "missing.json")

    def test_missing_capability_rejects_frontend_publish_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = write(root / "backend.json", {
                "image_digest": "sha256:" + "a" * 64, "source_sha": "abc1234", "schema_head": "head-1",
                "capabilities": ["chat-sse-v1"],
            })
            release = write(root / "admin.json", {"app": "admin", "required_backend_capabilities": ["admin-runtime-limits-v1"]})
            with self.assertRaisesRegex(CompatibilityError, "admin-runtime-limits-v1"):
                check_frontend_release(release, backend)

    def test_backend_upgrade_preserves_every_supported_frontend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tourist = write(root / "tourist.json", {"app": "tourist", "required_backend_capabilities": ["visitor-config-v1", "chat-sse-v1", "guide-context-v1"]})
            admin = write(root / "admin.json", {"app": "admin", "required_backend_capabilities": ["admin-runtime-limits-v1"]})
            candidate = write(root / "candidate.json", {
                "image_digest": "sha256:" + "d" * 64, "source_sha": "def4567", "schema_head": "head-2",
                "capabilities": ["visitor-config-v1", "chat-sse-v1", "guide-context-v1", "admin-runtime-limits-v1"],
            })
            self.assertEqual(check_backend_upgrade(candidate, [tourist, admin]), [])
            deficient = write(root / "deficient.json", {
                "image_digest": "sha256:" + "e" * 64, "source_sha": "abc7890", "schema_head": "head-2",
                "capabilities": ["visitor-config-v1", "admin-runtime-limits-v1"],
            })
            with self.assertRaisesRegex(CompatibilityError, "chat-sse-v1"):
                check_backend_upgrade(deficient, [tourist, admin])

    def test_health_status_is_not_a_compatibility_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = write(root / "backend.json", {"health": 200})
            release = write(root / "tourist.json", {"required_backend_capabilities": ["visitor-config-v1"]})
            with self.assertRaises(CompatibilityError):
                check_frontend_release(release, backend)


if __name__ == "__main__":
    unittest.main()
