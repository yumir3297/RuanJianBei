"""Exercise worker process shutdown against temporary SQLite, without providers."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from app.tests.async_db import open_test_session


@pytest.mark.parametrize("initialized", [True, False], ids=["empty-queue", "maintenance-error"])
def test_worker_cli_releases_database_and_exits(tmp_path, initialized):
    """An undisposed pooled connection must not keep --once alive after its cycle."""
    path = tmp_path / "worker-lifecycle.sqlite"
    if initialized:
        async def create_schema():
            engine, session = await open_test_session(str(path))
            try:
                await session.close()
            finally:
                await engine.dispose()
        asyncio.run(create_schema())

    backend = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [sys.executable, "-m", "app.services.tool_execution.worker", "--once",
         "--worker-id", "isolated-lifecycle-test"],
        cwd=tmp_path,
        env={
            "PATH": os.defpath,
            "PYTHONPATH": str(backend),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DATABASE_URL": f"sqlite+aiosqlite:///{path}",
            "LLM_PROVIDER": "stub", "ASR_PROVIDER": "stub", "VISION_PROVIDER": "stub",
        },
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()

    assert not timed_out, f"worker did not release its connections and exit: {stderr}"
    if initialized:
        assert process.returncode == 0, (stdout, stderr)
    else:
        assert process.returncode != 0
        assert "no such table" in stderr
    # A second SQLite client can immediately acquire and release a write lock.
    with sqlite3.connect(path, timeout=0) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        connection.rollback()
