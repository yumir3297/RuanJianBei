#!/usr/bin/env python3
"""Publish and roll back isolated tourist/admin static releases atomically."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
import fcntl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_release_compatibility import CompatibilityError, check_frontend_release  # noqa: E402

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ReleaseError(ValueError):
    pass


@contextmanager
def _deployment_lock(web: Path, lock_file: Path | None):
    lock_path = Path(lock_file) if lock_file else web.parent / ".deploy.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReleaseError(f"another release/deployment operation holds {lock_path}") from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, name: str) -> Path:
    rel = PurePosixPath(name)
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise ReleaseError(f"unsafe release path: {name}")
    path = root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ReleaseError(f"release path escapes root: {name}")
    return path


def _manifest(directory: Path) -> dict:
    try:
        data = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"invalid release manifest in {directory}") from exc
    if not isinstance(data, dict) or data.get("app") not in ("tourist", "admin") or not ID_RE.fullmatch(str(data.get("release_id", ""))):
        raise ReleaseError("release manifest requires app and safe release_id")
    files = data.get("files")
    if not isinstance(files, dict) or "index.html" not in files:
        raise ReleaseError("release manifest requires index.html and file hashes")
    for name, digest in files.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReleaseError("release file map contains invalid entry")
        path = _safe_file(directory, name)
        if not path.is_file() or _file_sha256(path) != digest:
            raise ReleaseError(f"release file missing or hash mismatch: {name}")
    return data


def _current(web: Path) -> Path | None:
    link = web / "current"
    if not link.exists() and not link.is_symlink():
        return None
    if not link.is_symlink():
        raise ReleaseError("current must be a symlink to a versioned release")
    resolved = link.resolve(strict=True)
    if not resolved.is_relative_to((web / "releases").resolve()):
        raise ReleaseError("current points outside this site's releases directory")
    _manifest(resolved)
    return resolved


def _copy_tree(source: Path, target: Path) -> None:
    for name in _manifest(source)["files"]:
        src = _safe_file(source, name)
        dst = _safe_file(target, name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if _file_sha256(dst) != _file_sha256(src):
                raise ReleaseError(f"asset filename collision with different content: {name}")
        else:
            shutil.copyfile(src, dst)


def _make_static_tree_readable(root: Path) -> None:
    """Static releases are public assets; make their tree traversable/readable by NGINX."""
    for path in root.rglob("*"):
        if path.is_dir():
            os.chmod(path, 0o755)
        elif path.is_file():
            os.chmod(path, 0o644)
    os.chmod(root, 0o755)


def _snapshot(web: Path, base: Path, extra: Path | None, release_id: str) -> Path:
    releases = web / "releases"
    web.mkdir(parents=True, exist_ok=True)
    os.chmod(web, 0o755)
    releases.mkdir(parents=True, exist_ok=True)
    if releases.is_symlink():
        raise ReleaseError("releases directory must not be a symlink")
    os.chmod(releases, 0o755)
    target = releases / release_id
    if target.exists():
        raise ReleaseError(f"release already exists: {release_id}")
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=releases))
    try:
        base_manifest = _manifest(base)
        if extra:
            extra_manifest = _manifest(extra)
            if extra_manifest["app"] != base_manifest["app"]:
                raise ReleaseError("cross-app asset merge is forbidden")
            # Keep every non-HTML file reachable by either active HTML/JS bundle.
            for source in (base, extra):
                for name in _manifest(source)["files"]:
                    if name != "index.html":
                        src, dst = _safe_file(source, name), _safe_file(stage, name)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if dst.exists() and _file_sha256(dst) != _file_sha256(src):
                            raise ReleaseError(f"asset filename collision with different content: {name}")
                        if not dst.exists():
                            shutil.copyfile(src, dst)
        _copy_tree(base, stage)
        manifest = dict(base_manifest)
        manifest["release_id"] = release_id
        manifest["files"] = {
            str(path.relative_to(stage).as_posix()): _file_sha256(path)
            for path in sorted(stage.rglob("*")) if path.is_file() and path.name != "release.json"
        }
        (stage / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _manifest(stage)
        _make_static_tree_readable(stage)
        os.replace(stage, target)
        return target
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _switch(web: Path, target: Path, old: Path | None) -> Path:
    web.mkdir(parents=True, exist_ok=True)
    if old:
        _replace_symlink(web / "previous", os.path.relpath(old, web))
    _replace_symlink(web / "current", os.path.relpath(target, web))
    return target


def _replace_symlink(link: Path, destination: str) -> None:
    temp = link.with_name(f".{link.name}.{os.getpid()}.tmp")
    temp.unlink(missing_ok=True)
    os.symlink(destination, temp)
    os.replace(temp, link)


def publish(web_root: Path, release_dir: Path, backend_release: Path, app: str | None = None, lock_file: Path | None = None) -> Path:
    web, source = Path(web_root).resolve(), Path(release_dir).resolve()
    with _deployment_lock(web, lock_file):
        candidate = _manifest(source)
        if app is not None and (app not in ("tourist", "admin") or app != candidate["app"]):
            raise ReleaseError("explicit app must be tourist/admin and match release manifest")
        try:
            check_frontend_release(source / "release.json", Path(backend_release))
        except CompatibilityError as exc:
            raise ReleaseError(str(exc)) from exc
        old = _current(web)
        if old and _manifest(old)["app"] != candidate["app"]:
            raise ReleaseError("cross-app publish is forbidden")
        target = _snapshot(web, source, old, candidate["release_id"])
        return _switch(web, target, old)


def rollback(web_root: Path, release_id: str, backend_release: Path, app: str | None = None, lock_file: Path | None = None) -> Path:
    web = Path(web_root).resolve()
    with _deployment_lock(web, lock_file):
        return _rollback_locked(web, release_id, backend_release, app)


def _rollback_locked(web: Path, release_id: str, backend_release: Path, app: str | None) -> Path:
    if app is not None and app not in ("tourist", "admin"):
        raise ReleaseError("app must be tourist or admin")
    if not ID_RE.fullmatch(release_id):
        raise ReleaseError("unsafe release id")
    old = _current(web)
    target_release = (web / "releases" / release_id).resolve(strict=True)
    if not target_release.is_relative_to((web / "releases").resolve()):
        raise ReleaseError("rollback target outside this site's release directory")
    target_manifest = _manifest(target_release)
    if target_manifest["release_id"] != release_id:
        raise ReleaseError("rollback release id does not match manifest")
    if app is not None and target_manifest["app"] != app:
        raise ReleaseError("explicit app does not match rollback manifest")
    if old and _manifest(old)["app"] != target_manifest["app"]:
        raise ReleaseError("cross-app rollback is forbidden")
    try:
        check_frontend_release(target_release / "release.json", Path(backend_release))
    except CompatibilityError as exc:
        raise ReleaseError(str(exc)) from exc
    rollback_id = "rollback-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = _snapshot(web, target_release, old, rollback_id)
    return _switch(web, target, old)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("publish", "rollback"):
        item = sub.add_parser(command)
        item.add_argument("--web-root", type=Path, required=True)
        item.add_argument("--backend-release", type=Path, required=True)
        item.add_argument("--app", choices=("tourist", "admin"), required=True)
        item.add_argument("--lock-file", type=Path, required=True)
        if command == "publish":
            item.add_argument("--release-dir", type=Path, required=True)
        else:
            item.add_argument("--release-id", required=True)
    args = parser.parse_args()
    try:
        result = publish(args.web_root, args.release_dir, args.backend_release, args.app, args.lock_file) if args.command == "publish" else rollback(args.web_root, args.release_id, args.backend_release, args.app, args.lock_file)
    except (ReleaseError, OSError) as exc:
        parser.exit(2, f"release rejected: {exc}\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
