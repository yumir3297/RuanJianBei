#!/usr/bin/env python3
"""Create candidate backend release metadata for the gated deployment script."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
SHA_RE = re.compile(r"[0-9a-fA-F]{7,64}")
SCHEMA_RE = re.compile(r"[A-Za-z0-9_.-]{1,128}")
CAPABILITY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


def package_backend_release(
    *, image_digest: str, schema_head: str, capabilities: list[str], output: Path,
    source_sha: str | None = None,
) -> Path:
    if not SHA256_RE.fullmatch(image_digest):
        raise ValueError("image digest must be the immutable Docker image ID (sha256:<64 lowercase hex>)")
    if not SCHEMA_RE.fullmatch(schema_head):
        raise ValueError("schema head is missing or invalid")
    if not capabilities or any(not CAPABILITY_RE.fullmatch(item) for item in capabilities):
        raise ValueError("at least one valid backend capability is required")
    if len(set(capabilities)) != len(capabilities):
        raise ValueError("duplicate backend capabilities are not allowed")
    if source_sha is None:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        if status.strip():
            raise ValueError("source worktree must be clean to derive its release SHA")
        source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not SHA_RE.fullmatch(source_sha):
        raise ValueError("source SHA must be a full or abbreviated git SHA")

    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("candidate output must be a new path")
    output.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "format": 1,
        "image_digest": image_digest,
        "source_sha": source_sha,
        "schema_head": schema_head,
        "capabilities": sorted(capabilities),
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=".backend-release-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, indent=2) + "\n")
            stream.flush()
        temporary.replace(output)
    except Exception:
        if temporary:
            temporary.unlink(missing_ok=True)
        raise
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-id", required=True, help="immutable docker image ID from docker image inspect --format '{{.Id}}'")
    parser.add_argument("--schema-head", required=True)
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--source-sha")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = package_backend_release(
            image_digest=args.image_id, schema_head=args.schema_head, capabilities=args.capability,
            output=args.output, source_sha=args.source_sha,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"backend release packaging failed: {exc}\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
