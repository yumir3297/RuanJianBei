"""Strict compatibility checks for static frontend and backend releases."""
from __future__ import annotations

import json
import argparse
from pathlib import Path
import re
from typing import Iterable


class CompatibilityError(ValueError):
    """Raised when release metadata cannot prove a safe version switch."""


def _read(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"{label} metadata unavailable: {path}") from exc
    if not isinstance(value, dict):
        raise CompatibilityError(f"{label} metadata must be an object")
    return value


def _strings(value: object, field: str, label: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise CompatibilityError(f"{label} {field} must be a list of non-empty strings")
    return set(value)


def _backend(path: Path) -> set[str]:
    data = _read(path, "backend release")
    if not isinstance(data.get("image_digest"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", data["image_digest"]):
        raise CompatibilityError("backend release missing valid image_digest")
    if not isinstance(data.get("source_sha"), str) or not re.fullmatch(r"[0-9a-fA-F]{7,64}", data["source_sha"]):
        raise CompatibilityError("backend release missing valid source_sha")
    if not isinstance(data.get("schema_head"), str) or not data["schema_head"].strip():
        raise CompatibilityError("backend release missing schema_head")
    return _strings(data.get("capabilities"), "capabilities", "backend release")


def _frontend(path: Path) -> tuple[str | None, set[str]]:
    data = _read(path, "frontend release")
    app = data.get("app")
    if app is not None and app not in ("tourist", "admin"):
        raise CompatibilityError("frontend release app must be tourist or admin")
    return app, _strings(data.get("required_backend_capabilities"), "required_backend_capabilities", "frontend release")


def check_frontend_release(release_path: Path, backend_path: Path) -> None:
    _, required = _frontend(Path(release_path))
    available = _backend(Path(backend_path))
    missing = sorted(required - available)
    if missing:
        raise CompatibilityError("backend lacks required capabilities: " + ", ".join(missing))


def check_backend_upgrade(candidate_path: Path, frontend_paths: Iterable[Path]) -> list[str]:
    available = _backend(Path(candidate_path))
    found_frontend = False
    for path in frontend_paths:
        app, required = _frontend(Path(path))
        missing = sorted(required - available)
        if missing:
            raise CompatibilityError(f"backend upgrade breaks {app or Path(path).name}: " + ", ".join(missing))
        found_frontend = True
    if not found_frontend:
        raise CompatibilityError("at least one supported frontend release is required")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    frontend = sub.add_parser("frontend")
    frontend.add_argument("--release", type=Path, required=True)
    frontend.add_argument("--backend", type=Path, required=True)
    backend = sub.add_parser("backend")
    backend.add_argument("--candidate", type=Path, required=True)
    backend.add_argument("--frontend", type=Path, action="append", required=True)
    args = parser.parse_args()
    try:
        if args.command == "frontend":
            check_frontend_release(args.release, args.backend)
        else:
            check_backend_upgrade(args.candidate, args.frontend)
    except CompatibilityError as exc:
        parser.exit(2, f"compatibility rejected: {exc}\n")
    print("compatibility metadata accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
