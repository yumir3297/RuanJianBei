#!/usr/bin/env python3
"""Explicit, quiesced state backup and isolated staging restore."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile


class BackupError(ValueError):
    pass


LABEL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$")


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    files = [path] if path.is_file() else [child for child in sorted(path.rglob("*")) if child.is_file()]
    for child in files:
        if child != path:
            digest.update(child.relative_to(path).as_posix().encode() + b"\0")
        with child.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def backup(output: Path, database_snapshot: Path, states: list[str], quiesced: bool) -> Path:
    if not quiesced:
        raise BackupError("backup requires --quiesced after API/worker writes are stopped")
    if not database_snapshot.is_file() or database_snapshot.is_symlink():
        raise BackupError("database snapshot must be an existing consistent dump/snapshot")
    entries: list[tuple[str, Path]] = [("database.snapshot", database_snapshot.resolve())]
    seen = {"database.snapshot"}
    for spec in states:
        if "=" not in spec:
            raise BackupError("state must use label=/absolute/or/relative/path")
        label, raw = spec.split("=", 1)
        if not LABEL.fullmatch(label) or label in seen:
            raise BackupError(f"invalid or duplicate state label: {label}")
        unresolved = Path(raw)
        if not unresolved.exists() or unresolved.is_symlink():
            raise BackupError(f"state path missing or symlink: {unresolved}")
        path = unresolved.resolve()
        if path.is_dir() and any(child.is_symlink() for child in path.rglob("*")):
            raise BackupError(f"state tree contains symlinks and cannot be snapshotted safely: {path}")
        seen.add(label)
        entries.append((label, path))
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise BackupError("backup output already exists; use a new destination")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="backup-stage-", dir=output.parent) as temp_name:
        stage = Path(temp_name)
        manifest = []
        for name, source in entries:
            target = stage / name
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            manifest.append({"name": name, "sha256": _digest(target), "directory": target.is_dir()})
        (stage / "backup-manifest.json").write_text(json.dumps({"format": 1, "entries": manifest}, indent=2) + "\n", encoding="utf-8")
        temp_archive = output.with_name(f".{output.name}.tmp")
        try:
            with tarfile.open(temp_archive, "w:gz") as archive:
                for child in sorted(stage.iterdir()):
                    archive.add(child, arcname=child.name, recursive=True)
            temp_archive.replace(output)
        finally:
            temp_archive.unlink(missing_ok=True)
    return output


def restore(archive_path: Path, target: Path) -> Path:
    target = target.absolute()
    if not target.name.startswith(("restore-", ".restore-")):
        raise BackupError("restore target must be a dedicated restore-* staging directory")
    if target.exists() or target.is_symlink():
        raise BackupError("restore target must not exist; restore never overlays existing data")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".restore-stage-", dir=target.parent) as temp_name:
        stage = Path(temp_name)
        try:
            with tarfile.open(archive_path, "r:gz") as bundle:
                members = bundle.getmembers()
                for member in members:
                    item = PurePosixPath(member.name)
                    if item.is_absolute() or any(part in ("", ".", "..") for part in item.parts) or member.issym() or member.islnk():
                        raise BackupError(f"unsafe backup member: {member.name}")
                bundle.extractall(stage, members=members, filter="data")
        except (OSError, tarfile.TarError) as exc:
            raise BackupError(f"cannot read backup archive: {exc}") from exc
        try:
            manifest = json.loads((stage / "backup-manifest.json").read_text(encoding="utf-8"))
            entries = manifest["entries"]
            if manifest.get("format") != 1 or not isinstance(entries, list) or not entries:
                raise ValueError("unsupported or empty backup manifest")
            names = set()
            for entry in entries:
                name = entry["name"]
                if not LABEL.fullmatch(name) and name != "database.snapshot":
                    raise ValueError("invalid entry name")
                if name in names:
                    raise ValueError("duplicate entry")
                names.add(name)
                content = stage / name
                if not content.exists() or content.is_symlink() or _digest(content) != entry["sha256"]:
                    raise ValueError(f"backup content hash mismatch: {name}")
            if "database.snapshot" not in names:
                raise ValueError("backup does not contain database snapshot")
        except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise BackupError(f"backup verification failed: {exc}") from exc
        (stage / "RESTORE-ISOLATED-STAGING.txt").write_text("Verified files for operator-controlled recovery. No database or service was modified.\n", encoding="utf-8")
        stage.rename(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--quiesced", action="store_true")
    b.add_argument("--database-snapshot", type=Path, required=True)
    b.add_argument("--state", action="append", default=[])
    b.add_argument("--output", type=Path, required=True)
    r = sub.add_parser("restore")
    r.add_argument("--archive", type=Path, required=True)
    r.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = backup(args.output, args.database_snapshot, args.state, args.quiesced) if args.command == "backup" else restore(args.archive, args.target)
    except (BackupError, OSError) as exc:
        parser.exit(2, f"backup/restore rejected: {exc}\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
