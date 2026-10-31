import asyncio
import sys

import pytest

from app.services.rag.index_write_lock import index_write_lock


def test_lock_excludes_another_process_and_releases_after_exit(tmp_path):
    async def scenario():
        path = tmp_path / "index.lock"
        script = (
            "import asyncio,sys\n"
            "from pathlib import Path\n"
            "from app.services.rag.index_write_lock import index_write_lock\n"
            "async def run():\n"
            " async with index_write_lock(Path(sys.argv[1]), timeout=2):\n"
            "  print('acquired', flush=True)\n"
            "  await asyncio.sleep(60)\n"
            "asyncio.run(run())\n"
        )
        child = await asyncio.create_subprocess_exec(sys.executable, "-c", script, str(path),
            stdout=asyncio.subprocess.PIPE)
        try:
            assert await asyncio.wait_for(child.stdout.readline(), 3) == b"acquired\n"
            with pytest.raises(TimeoutError):
                async with index_write_lock(path, timeout=0.1):
                    pass
        finally:
            child.kill()
            await child.wait()
        async with index_write_lock(path, timeout=1):
            pass

    asyncio.run(scenario())


def test_cancellation_does_not_leave_lock_held(tmp_path):
    async def scenario():
        path = tmp_path / "index.lock"
        entered = asyncio.Event()

        async def holder():
            async with index_write_lock(path, timeout=1):
                entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(holder())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with index_write_lock(path, timeout=1):
            pass

    asyncio.run(scenario())
