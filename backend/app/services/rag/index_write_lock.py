"""Cross-process advisory lock for writers sharing a local index directory."""
from __future__ import annotations

import asyncio
import errno
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic


def _try_lock(handle) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as error:
        if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
            return False
        raise


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@asynccontextmanager
async def index_write_lock(path: Path, *, timeout: float = 30):
    """Lock a stable file; all writers must use the same local filesystem path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        # Windows byte-range locks require a byte to exist.
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = monotonic() + max(timeout, 0)
        while not _try_lock(handle):
            if monotonic() >= deadline:
                raise TimeoutError("等待知识索引写入锁超时，请稍后重试")
            await asyncio.sleep(min(0.05, max(0, deadline - monotonic())))
        try:
            yield
        finally:
            _unlock(handle)
