from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import socket
import uuid

from app.db.session import AsyncSessionLocal, engine
from app.repositories.tool_execution import ToolExecutionRepository
from app.services.tool_execution.handlers import build_registry
from app.services.tool_execution.runner import ToolRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("tool_execution.worker")


async def _maintenance() -> None:
    async with AsyncSessionLocal() as session:
        changed = await ToolExecutionRepository(session).maintain()
    if any(changed.values()):
        logger.info("maintenance updated execution records: %s", changed)


async def serve(worker_id: str, once: bool = False, poll_seconds: float = 1.0) -> None:
    registry = build_registry()
    await _maintenance()
    if not len(registry):
        logger.warning("tool registry is empty; no jobs will be claimed")
        return
    runner = ToolRunner(AsyncSessionLocal, registry)
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stopping.set)
        except NotImplementedError:
            pass
    while not stopping.is_set():
        try:
            did_work = await runner.run_one(worker_id)
            await _maintenance()
        except Exception:
            logger.exception("worker iteration failed")
            did_work = False
        if once:
            break
        if not did_work:
            try:
                await asyncio.wait_for(stopping.wait(), timeout=max(0.1, poll_seconds))
            except asyncio.TimeoutError:
                pass


async def _run_cli(worker_id: str, once: bool, poll_seconds: float) -> None:
    try:
        await serve(worker_id, once, poll_seconds)
    finally:
        # The CLI owns the global engine. Close pooled connections while the
        # event loop is still running, including failed startup and shutdown.
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a separate durable tool-execution worker")
    parser.add_argument("--worker-id", default=f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--once", action="store_true", help="run one claim cycle and exit")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    asyncio.run(_run_cli(args.worker_id, args.once, args.poll_seconds))


if __name__ == "__main__":
    main()
