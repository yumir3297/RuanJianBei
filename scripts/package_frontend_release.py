#!/usr/bin/env python3
"""Package one built app with a strict, file-hashed release manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = {
    "tourist": ["visitor-config-v1", "chat-sse-v1", "tourist-feedback-v1", "guide-context-v1"],
    "admin": ["admin-runtime-limits-v1", "admin-auth-v1", "knowledge-import-v1"],
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package(app: str, release_id: str, dist: Path, output: Path, source_sha: str | None = None) -> Path:
    if app not in CAPABILITIES or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id):
        raise ValueError("app must be tourist/admin and release id must be safe")
    dist, output = dist.resolve(), output.resolve()
    if dist != (ROOT / "frontend/dist" / app).resolve():
        raise ValueError("dist path must match the selected isolated app output")
    if not (dist / "index.html").is_file():
        raise ValueError("built app directory must contain index.html")
    if output.exists():
        raise ValueError("release output must not already exist")
    if source_sha is None:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        if status.strip():
            raise ValueError("source worktree must be clean to derive its release SHA")
        source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", source_sha):
        raise ValueError("source SHA must be a full or abbreviated git SHA")
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    vite_version = lock.get("packages", {}).get("node_modules/vite", {}).get("version")
    if not vite_version:
        raise ValueError("package lock does not contain a resolved Vite version")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".release-stage-", dir=output.parent))
    try:
        shutil.copytree(dist, stage, dirs_exist_ok=True)
        files = {
            path.relative_to(stage).as_posix(): file_sha256(path)
            for path in sorted(stage.rglob("*")) if path.is_file()
        }
        manifest = {
            "format": 1, "app": app, "release_id": release_id, "source_sha": source_sha,
            "build_tool": {"name": "Vite", "version": vite_version},
            "required_backend_capabilities": CAPABILITIES[app], "files": files,
        }
        (stage / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        stage.rename(output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", choices=tuple(CAPABILITIES), required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha")
    args = parser.parse_args()
    try:
        result = package(args.app, args.release_id, args.dist, args.output, args.source_sha)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"release packaging failed: {exc}\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
