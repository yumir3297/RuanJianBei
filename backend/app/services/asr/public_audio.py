from __future__ import annotations

import time
from pathlib import Path


def cleanup_expired_public_audio(
    upload_root: Path,
    retention_seconds: int,
    *,
    now: float | None = None,
) -> int:
    """Remove expired temporary audio files and return the number removed."""
    if not upload_root.exists():
        return 0

    current_time = time.time() if now is None else now
    removed = 0
    for path in upload_root.iterdir():
        try:
            if not path.is_file() and not path.is_symlink():
                continue
            if current_time - path.stat().st_mtime <= retention_seconds:
                continue
            path.unlink()
            removed += 1
        except FileNotFoundError:
            continue
    return removed
