from __future__ import annotations

import sys
from pathlib import Path

from common import root_dir, sha256_file


def main() -> int:
    root = root_dir()
    checksum_file = root / "CHECKSUMS.sha256"
    if not checksum_file.exists():
        print("Missing CHECKSUMS.sha256", file=sys.stderr)
        return 2
    failures: list[str] = []
    checked = 0
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        expected, relative = line.split("  ", 1)
        path = root / Path(relative)
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        actual = sha256_file(path)
        checked += 1
        if actual != expected:
            failures.append(f"hash mismatch: {relative}: {actual}")
    if failures:
        print("Bundle verification FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Bundle verification passed: {checked} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
