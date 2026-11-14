"""Compare the real local chat endpoint with GuideMatch off and on.

Runs against a new temporary database and synthetic FAQ only.
"""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

import httpx


def main():
    backend = Path(__file__).resolve().parent
    model = os.environ.get("GUIDEMATCH_MODEL_DIR")
    if not model or not Path(model).is_absolute():
        raise SystemExit("Set GUIDEMATCH_MODEL_DIR to the absolute local model directory")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="guidematch-api-") as directory:
        root = Path(directory)
        env = {
            "PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(backend),
            "DATABASE_URL": "sqlite+aiosqlite:///" + str(root / "demo.sqlite"),
            "APP_ENV": "test", "SITE_ID": "demo", "ENABLE_SAMPLE_DATA": "false",
            "LLM_PROVIDER": "stub", "TTS_PROVIDER": "stub", "EMBEDDING_MODEL_NAME": "simple-dev-embedder",
            "CHROMA_PERSIST_DIR": str(root / "chroma"), "KNOWLEDGE_UPLOAD_DIR": str(root / "knowledge"),
            "UI_ASSET_UPLOAD_DIR": str(root / "ui"), "UI_ASSET_MANIFEST_PATH": str(root / "ui.json"),
            "GUIDEMATCH_MODEL_DIR": model, "GUIDEMATCH_DEVICE": os.environ.get("GUIDEMATCH_DEVICE", "cpu"),
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        }
        subprocess.run([sys.executable, "-m", "app.cli.deployment", "migrate"], cwd=directory, env=env, check=True)
        with sqlite3.connect(root / "demo.sqlite") as db:
            db.execute(
                "INSERT INTO faq_entries (id, category, aliases_json, answer, sources_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                ("demo", "general", json.dumps(["从门口到大佛要走多久？"], ensure_ascii=False),
                 "合成FAQ位置答案", json.dumps(["本地合成"], ensure_ascii=False)),
            )
        for enabled in (False, True):
            env["GUIDEMATCH_ENABLED"] = str(enabled).lower()
            log = open(root / f"api-{enabled}.log", "w+", encoding="utf-8")
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=directory, env=env, stdout=log, stderr=log)
            try:
                origin = f"http://127.0.0.1:{port}"
                for _ in range(150):
                    if server.poll() is not None:
                        raise RuntimeError("local API stopped before startup")
                    try:
                        if httpx.get(origin + "/health", timeout=0.5).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("local API startup timed out")
                for query, expected in (("从门口到灌浴要走多久？", not enabled), ("从门口到大佛要走多久？", True)):
                    response = httpx.post(origin + "/api/chat/stream", json={"query": query, "session_id": f"smoke-{enabled}-{query}", "text_only": True}, timeout=60)
                    response.raise_for_status()
                    assert "event: done" in response.text, "missing SSE done"
                    assert ("合成FAQ位置答案" in response.text) is expected, (enabled, query, response.text)
                    print(f"GuideMatch {'on' if enabled else 'off'}: {query} FAQ reuse={expected} PASS", flush=True)
                log.flush()
                log.seek(0)
                assert "GuideMatch unavailable" not in log.read(), "model failed to load in API process"
            finally:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
                log.close()


if __name__ == "__main__":
    main()
