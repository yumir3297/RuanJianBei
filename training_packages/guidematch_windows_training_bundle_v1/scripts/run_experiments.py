from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import environment_info, read_json, root_dir, write_json


def run(command: list[str], cwd: Path) -> None:
    print("\n>>", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = root_dir()
    config_path = args.config if args.config.is_absolute() else root / args.config
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    config = read_json(config_path)
    environment = environment_info()
    write_json(output / "environment.json", environment)
    if config.get("require_cuda", True) and not environment.get("cuda_available"):
        raise RuntimeError("CUDA GPU is required. Refusing silent CPU fallback.")

    run(
        [
            sys.executable,
            str(root / "scripts/baseline_tfidf.py"),
            "--output-dir",
            str(output / "baseline_tfidf"),
        ],
        root,
    )
    for stage in config["stages"]:
        for seed in config["seeds"]:
            run_dir = output / "runs" / f"{stage}-seed{seed}"
            run(
                [
                    sys.executable,
                    str(root / "scripts/train_guidematch.py"),
                    "--config",
                    str(config_path),
                    "--model-source",
                    args.model_source,
                    "--stage",
                    str(stage),
                    "--seed",
                    str(seed),
                    "--output-dir",
                    str(run_dir),
                ],
                root,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
