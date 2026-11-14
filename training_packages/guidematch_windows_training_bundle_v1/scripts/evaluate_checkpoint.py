from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from common import read_jsonl, root_dir, write_json
from modeling import GuideMatchModel
from train_guidematch import PairDataset, evaluate, make_collate


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate one frozen checkpoint on a new labeled JSONL file.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model-source", help="Optional fallback if checkpoint/encoder_config is absent")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    root = root_dir()
    checkpoint_path = args.checkpoint if args.checkpoint.is_absolute() else root / args.checkpoint
    data_path = args.data if args.data.is_absolute() else root / args.data
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    labels = payload["labels"]
    reasons = payload["reasons"]
    metadata = payload["metadata"]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint_path.parent / "tokenizer")
    encoder_config = checkpoint_path.parent / "encoder_config"
    architecture_source = str(encoder_config if encoder_config.exists() else args.model_source or "")
    if not architecture_source:
        raise RuntimeError("Checkpoint lacks encoder_config; provide --model-source")
    model = GuideMatchModel(
        architecture_source,
        len(labels),
        len(reasons),
        float(metadata["config"]["dropout"]),
        load_pretrained=False,
    )
    model.load_state_dict(payload["state_dict"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    rows = read_jsonl(data_path)
    loader = DataLoader(
        PairDataset(rows, {label: i for i, label in enumerate(labels)}, {reason: i for i, reason in enumerate(reasons)}),
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=make_collate(tokenizer, int(metadata["config"]["max_length"])),
    )
    metrics, predictions = evaluate(model, loader, device, labels, reasons)
    write_json(output / "metrics.json", metrics)
    with (output / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Evaluation complete: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
