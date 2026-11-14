from __future__ import annotations

import hashlib
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy/scripts"))
from static_release import ReleaseError, publish, rollback  # noqa: E402


def make_release(root: Path, app: str, release_id: str, assets: dict[str, str]) -> Path:
    directory = root / f"{app}-{release_id}"
    directory.mkdir()
    files = {"index.html": f"<script src='/assets/{release_id}.js'></script>",
             **{f"assets/{name}": content for name, content in assets.items()}}
    for name, content in files.items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest = {
        "app": app, "release_id": release_id,
        "required_backend_capabilities": ["visitor-config-v1", "guide-context-v1"] if app == "tourist" else ["admin-runtime-limits-v1"],
        "files": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()},
    }
    (directory / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def backend(root: Path) -> Path:
    path = root / "backend.json"
    path.write_text(json.dumps({"image_digest": "sha256:" + "a" * 64, "source_sha": "abcdef0", "schema_head": "head", "capabilities": ["visitor-config-v1", "guide-context-v1", "admin-runtime-limits-v1"]}), encoding="utf-8")
    return path


class StaticReleaseTests(unittest.TestCase):
    def test_published_release_is_readable_by_nginx_under_restrictive_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = make_release(root, "tourist", "t1", {"app.js": "public asset"})
            web = root / "web"
            previous_umask = os.umask(0o077)
            try:
                current = publish(web, release, backend(root), "tourist")
            finally:
                os.umask(previous_umask)

            directories = [web, web / "releases", current, *(path for path in current.rglob("*") if path.is_dir())]
            for path in directories:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o005, 0o005, f"NGINX cannot traverse {path}")
            for path in (path for path in current.rglob("*") if path.is_file()):
                self.assertTrue(stat.S_IMODE(path.stat().st_mode) & 0o004, f"NGINX cannot read {path}")

    def test_publish_and_rollback_keep_both_asset_sets_reachable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = make_release(root, "tourist", "a1", {"old.js": "old-a"})
            b = make_release(root, "tourist", "b2", {"new.js": "new-b"})
            web = root / "web"
            current = publish(web, a, backend(root))
            current = publish(web, b, backend(root))
            self.assertTrue((current / "assets/old.js").is_file())
            self.assertTrue((current / "assets/new.js").is_file())
            rolled = rollback(web, "a1", backend(root))
            self.assertTrue((rolled / "assets/old.js").is_file())
            self.assertTrue((rolled / "assets/new.js").is_file())
            self.assertIn("a1", (rolled / "index.html").read_text())

    def test_publish_rejects_cross_app_and_hash_name_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend_path = backend(root)
            tourist = make_release(root, "tourist", "t1", {"shared.js": "tourist"})
            admin = make_release(root, "admin", "a1", {"admin.js": "admin"})
            web = root / "web"
            publish(web, tourist, backend_path)
            with self.assertRaises(ReleaseError):
                publish(web, admin, backend_path)
            altered = make_release(root, "tourist", "t2", {"shared.js": "other-content"})
            # Identical logical asset name with different bytes is rejected if its name is content-hashed.
            with self.assertRaises(ReleaseError):
                publish(web, altered, backend_path)

    def test_unknown_app_and_traversal_release_id_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "web"
            with self.assertRaises(ReleaseError):
                rollback(web, "../../admin", backend(root))

    def test_publish_and_rollback_require_backend_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tourist = make_release(root, "tourist", "t1", {"old.js": "old"})
            insufficient = root / "insufficient.json"
            insufficient.write_text(json.dumps({"image_digest": "sha256:" + "b" * 64, "source_sha": "abcdef0", "schema_head": "head", "capabilities": []}), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseError, "guide-context-v1"):
                publish(root / "web", tourist, insufficient, "tourist")
            web = root / "web"
            publish(web, tourist, backend(root), "tourist")
            with self.assertRaisesRegex(ReleaseError, "guide-context-v1"):
                rollback(web, "t1", insufficient, "tourist")

    def test_release_operation_fails_while_shared_deployment_lock_is_held(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = make_release(root, "tourist", "t1", {"old.js": "old"})
            lock = root / "deployment.lock"
            descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ReleaseError, "another release/deployment"):
                    publish(root / "web", release, backend(root), "tourist", lock)
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)


if __name__ == "__main__":
    unittest.main()
