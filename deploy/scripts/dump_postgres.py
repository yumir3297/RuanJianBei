#!/usr/bin/env python3
"""Create a PostgreSQL custom-format snapshot without putting its password in argv."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(raw)
    if parsed.scheme not in ("postgres", "postgresql", "postgresql+asyncpg") or not parsed.hostname or not parsed.path.strip("/"):
        parser.error("DATABASE_URL must identify the configured PostgreSQL database")
    executable = shutil.which("pg_dump")
    if not executable:
        parser.error("pg_dump is required on the deployment host")
    env = os.environ.copy()
    if parsed.password is not None:
        env["PGPASSWORD"] = unquote(parsed.password)
    query = dict(item.split("=", 1) for item in parsed.query.split("&") if "=" in item)
    if query.get("sslmode"):
        env["PGSSLMODE"] = query["sslmode"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [executable, "--format=custom", "--no-owner", "--no-acl", "--host", parsed.hostname,
               "--port", str(parsed.port or 5432), "--username", unquote(parsed.username or ""),
               "--dbname", unquote(parsed.path.lstrip("/")), "--file", str(args.output)]
    result = subprocess.run(command, env=env, check=False)
    if result.returncode:
        args.output.unlink(missing_ok=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
