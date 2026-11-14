from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy/scripts"))
from backup_restore import BackupError, backup, restore  # noqa: E402


class BackupRestoreTests(unittest.TestCase):
    def test_backup_requires_quiescence_and_restore_isolated_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "db.dump"
            db.write_bytes(b"db-snapshot")
            upload = root / "uploads"
            upload.mkdir()
            (upload / "image.bin").write_bytes(b"asset")
            archive = root / "backup.tar.gz"
            with self.assertRaises(BackupError):
                backup(archive, db, [f"uploads={upload}"], False)
            backup(archive, db, [f"uploads={upload}"], True)
            with self.assertRaises(BackupError):
                restore(archive, root / "production")
            target = restore(archive, root / "restore-rehearsal")
            self.assertEqual((target / "database.snapshot").read_bytes(), b"db-snapshot")
            self.assertEqual((target / "uploads/image.bin").read_bytes(), b"asset")
            self.assertFalse((target / "production").exists())

    def test_restore_refuses_to_overlay_even_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "db.dump"
            db.write_bytes(b"snapshot")
            archive = backup(root / "backup.tar.gz", db, [], True)
            with self.assertRaises(BackupError):
                backup(archive, db, [], True)
            target = root / "restore-existing"
            target.mkdir()
            with self.assertRaises(BackupError):
                restore(archive, target)

    def test_backup_rejects_symlinked_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "db.dump"
            actual.write_bytes(b"snapshot")
            link = root / "db-link.dump"
            link.symlink_to(actual)
            with self.assertRaises(BackupError):
                backup(root / "backup.tar.gz", link, [], True)


if __name__ == "__main__":
    unittest.main()
