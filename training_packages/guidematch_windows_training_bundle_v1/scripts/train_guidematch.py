from __future__ import annotations

import argparse
import copy
import json
import math
import time
import random
import os
import numpy as np
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from common import (
    deterministic_guard,
    environment_info,
    metrics_from_predictions,
    read_json,
    read_jsonl,
    root_dir,
    sha256_file,
    set_seed,
    write_json,
)
from modeling import GuideMatchModel


class PairDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], label_map: dict[str, int], reason_map: dict[str, int]) -> None:
        self.rows = rows
        self.label_map = label_map
        self.reason_map = reason_map

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.rows[index]
        return {
            "left": row["left"]["text"],
            "right": row["right"]["text"],
            "label": self.label_map[row["expected"]],
            "reason": self.reason_map[row["reason"]],
            "row": row,
        }


def make_collate(tokenizer: Any, max_length: int):
    def collate(items: list[dict[str, Any]]) -> dict[str, Any]:
        tokens = tokenizer(
            [item["left"] for item in items],
            [item["right"] for item in items],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        return {
            "tokens": tokens,
            "labels": torch.tensor([item["label"] for item in items], dtype=torch.long),
            "reasons": torch.tensor([item["reason"] for item in items], dtype=torch.long),
            "rows": [item["row"] for item in items],
        }

    return collate


def augmented_rows(rows: list[dict[str, Any]], enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return rows
    result = list(rows)
    for row in rows:
        swapped = copy.deepcopy(row)
        swapped["case_id"] = f"{row['case_id']}::swapped"
        swapped["left"], swapped["right"] = swapped["right"], swapped["left"]
        result.append(swapped)
    return result


@torch.no_grad()
def evaluate(
    model: GuideMatchModel,
    loader: DataLoader,
    device: torch.device,
    labels: list[str],
    reasons: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    model.eval()
    truth: list[str] = []
    raw_predictions: list[str] = []
    guarded_predictions: list[str] = []
    reason_truth: list[str] = []
    reason_predictions: list[str] = []
    output_rows: list[dict[str, Any]] = []
    for batch in loader:
        tokens = {key: value.to(device) for key, value in batch["tokens"].items()}
        label_logits, reason_logits = model(**tokens)
        probabilities = label_logits.softmax(dim=-1).cpu()
        reason_probabilities = reason_logits.softmax(dim=-1).cpu()
        guesses = probabilities.argmax(dim=-1).tolist()
        reason_guesses = reason_probabilities.argmax(dim=-1).tolist()
        for row, guess, reason_guess, probs in zip(batch["rows"], guesses, reason_guesses, probabilities.tolist()):
            raw = labels[guess]
            guard = deterministic_guard(row)
            guarded = guard or raw
            truth.append(row["expected"])
            raw_predictions.append(raw)
            guarded_predictions.append(guarded)
            reason_truth.append(row["reason"])
            reason_predictions.append(reasons[reason_guess])
            output_rows.append(
                {
                    "case_id": row["case_id"],
                    "expected": row["expected"],
                    "raw_predicted": raw,
                    "guarded_predicted": guarded,
                    "guard_applied": guard is not None,
                    "label_probabilities": dict(zip(labels, probs)),
                    "reason_predicted": reasons[reason_guess],
                }
            )
    reason_metrics = metrics_from_predictions(reason_truth, reason_predictions, reasons)
    reason_metrics.pop("false_reuse_count", None)
    reason_metrics.pop("false_reuse_denominator", None)
    reason_metrics.pop("false_reuse_rate", None)
    return {
        "raw": metrics_from_predictions(truth, raw_predictions, labels),
        "guarded": metrics_from_predictions(truth, guarded_predictions, labels),
        "auxiliary_reason": reason_metrics,
    }, output_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--stage", choices=["frozen", "last_layer"], required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path, default=None, help="checkpoint.pt or a run directory containing it")
    args = parser.parse_args()

    root = root_dir()
    config_path = args.config if args.config.is_absolute() else root / args.config
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config = read_json(config_path)
    labels = list(config["labels"])
    reasons = list(config["reasons"])
    label_map = {label: index for index, label in enumerate(labels)}
    reason_map = {reason: index for index, reason in enumerate(reasons)}
    set_seed(args.seed)

    if config.get("require_cuda", True) and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required but unavailable. Fix the NVIDIA/PyTorch environment; CPU fallback is disabled.")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    write_json(output_dir / "environment.json", environment_info())

    train_rows = augmented_rows(
        read_jsonl(root / "data/splits/train.jsonl"), bool(config.get("augment_swap", True))
    )
    dev_rows = read_jsonl(root / "data/splits/dev.jsonl")
    tokenizer = AutoTokenizer.from_pretrained(args.model_source)
    model = GuideMatchModel(
        args.model_source,
        num_labels=len(labels),
        num_reasons=len(reasons),
        dropout=float(config["dropout"]),
    )
    parameter_info = model.configure_stage(args.stage)
    model.to(device)

    collate = make_collate(tokenizer, int(config["max_length"]))
    train_loader = DataLoader(
        PairDataset(train_rows, label_map, reason_map),
        batch_size=int(config["batch_size"]),
        shuffle=True,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=collate,
        pin_memory=device.type == "cuda",
    )
    dev_loader = DataLoader(
        PairDataset(dev_rows, label_map, reason_map),
        batch_size=int(config["batch_size"]) * 2,
        shuffle=False,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=collate,
        pin_memory=device.type == "cuda",
    )

    head_parameters = list(model.label_head.parameters()) + list(model.reason_head.parameters())
    encoder_parameters = [parameter for parameter in model.encoder.parameters() if parameter.requires_grad]
    groups = [{"params": head_parameters, "lr": float(config["learning_rate_head"])}]
    if encoder_parameters:
        groups.append({"params": encoder_parameters, "lr": float(config["learning_rate_encoder"])})
    optimizer = AdamW(groups, weight_decay=float(config["weight_decay"]))
    accumulation = int(config["gradient_accumulation_steps"])
    total_steps = math.ceil(len(train_loader) / accumulation) * int(config["epochs"])
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(total_steps * 0.1)),
        num_training_steps=total_steps,
    )
    label_loss_fn = nn.CrossEntropyLoss(label_smoothing=float(config["label_smoothing"]))
    reason_loss_fn = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_score = -1.0
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    patience = 0
    history: list[dict[str, Any]] = []
    start_epoch = 1
    data_hashes = {name: sha256_file(root / "data/splits" / f"{name}.jsonl") for name in ("train", "dev")}
    training_complete = False
    resume_path = args.resume_from
    if resume_path is not None:
        resume_path = resume_path if resume_path.is_absolute() else root / resume_path
        if resume_path.is_dir():
            resume_path = resume_path / "checkpoint.pt"
        if not resume_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")
        checkpoint = torch.load(resume_path, map_location="cpu", weights_only=True)
        saved_meta = checkpoint.get("metadata", {})
        if saved_meta.get("stage") != args.stage or saved_meta.get("seed") != args.seed:
            raise ValueError("Resume checkpoint stage/seed does not match this run")
        if saved_meta.get("model_source") != args.model_source:
            raise ValueError("Resume checkpoint model source does not match this run")
        if saved_meta.get("config") != config or saved_meta.get("data_hashes") != data_hashes:
            raise ValueError("Resume checkpoint configuration or training data differs from this run")
        if saved_meta.get("device_type") != device.type:
            raise ValueError("Resume checkpoint device type differs from this run")
        model.load_state_dict(checkpoint["model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        scheduler.load_state_dict(checkpoint["scheduler_state"])
        scaler.load_state_dict(checkpoint["scaler_state"])
        best_score = float(checkpoint.get("best_score", -1.0))
        best_epoch = int(checkpoint.get("best_epoch", 0))
        best_state = checkpoint.get("best_state")
        patience = int(checkpoint.get("patience", 0))
        history = list(checkpoint.get("history", []))
        start_epoch = int(checkpoint["epoch"]) + 1
        if start_epoch > int(config["epochs"]) + 1:
            raise ValueError("Resume checkpoint epoch exceeds configured epochs")
        training_complete = bool(checkpoint.get("training_complete"))
        random.setstate(checkpoint["python_rng_state"])
        torch.set_rng_state(checkpoint["torch_rng_state"])
        numpy_state = checkpoint["numpy_rng_state"]
        np.random.set_state((numpy_state[0], np.asarray(numpy_state[1], dtype=np.uint32), *numpy_state[2:]))
        if device.type == "cuda" and checkpoint.get("cuda_rng_state_all") is not None:
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state_all"])
        print(f"Resuming {args.stage} seed={args.seed} at epoch {start_epoch} from {resume_path}")
    started = time.time()
    for epoch in range(start_epoch, int(config["epochs"]) + 1) if not training_complete else ():
        model.train()
        if args.stage == "frozen":
            model.encoder.eval()
        optimizer.zero_grad(set_to_none=True)
        running_loss = 0.0
        progress = tqdm(train_loader, desc=f"{args.stage} seed={args.seed} epoch={epoch}")
        for step, batch in enumerate(progress, 1):
            tokens = {key: value.to(device) for key, value in batch["tokens"].items()}
            targets = batch["labels"].to(device)
            reason_targets = batch["reasons"].to(device)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                label_logits, reason_logits = model(**tokens)
                main_loss = label_loss_fn(label_logits, targets)
                auxiliary_loss = reason_loss_fn(reason_logits, reason_targets)
                non_reuse = targets != label_map["reuse"]
                if non_reuse.any():
                    risk_loss = label_logits.softmax(dim=-1)[non_reuse, label_map["reuse"]].mean()
                else:
                    risk_loss = label_logits.sum() * 0.0
                loss = (
                    main_loss
                    + float(config["aux_loss_weight"]) * auxiliary_loss
                    + float(config["false_reuse_penalty"]) * risk_loss
                ) / accumulation
            scaler.scale(loss).backward()
            if step % accumulation == 0 or step == len(train_loader):
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), float(config["max_grad_norm"]))
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            running_loss += float(loss.item()) * accumulation
            progress.set_postfix(loss=f"{running_loss / step:.4f}")

        dev_metrics, _ = evaluate(model, dev_loader, device, labels, reasons)
        score = float(dev_metrics["raw"][config["selection_metric"]])
        history.append(
            {
                "epoch": epoch,
                "train_loss": running_loss / len(train_loader),
                "raw_macro_f1": dev_metrics["raw"]["macro_f1"],
                "raw_false_reuse_rate": dev_metrics["raw"]["false_reuse_rate"],
            }
        )
        if score > best_score + 1e-6:
            best_score = score
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        should_stop = patience >= int(config["early_stopping_patience"])

        checkpoint_metadata = {
            "model_source": args.model_source,
            "stage": args.stage,
            "seed": args.seed,
            "config": config,
            "epoch": epoch,
            "data_hashes": data_hashes,
            "device_type": device.type,
        }
        numpy_state = np.random.get_state()
        temporary_checkpoint = output_dir / "checkpoint.pt.tmp"
        torch.save(
            {
                "epoch": epoch,
                "training_complete": should_stop or epoch == int(config["epochs"]),
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "scheduler_state": scheduler.state_dict(),
                "scaler_state": scaler.state_dict(),
                "best_state": best_state,
                "best_score": best_score,
                "best_epoch": best_epoch,
                "patience": patience,
                "history": history,
                "metadata": checkpoint_metadata,
                "python_rng_state": random.getstate(),
                "torch_rng_state": torch.get_rng_state(),
                "numpy_rng_state": (numpy_state[0], numpy_state[1].tolist(), *numpy_state[2:]),
                "cuda_rng_state_all": torch.cuda.get_rng_state_all() if device.type == "cuda" else None,
            },
            temporary_checkpoint,
        )
        os.replace(temporary_checkpoint, output_dir / "checkpoint.pt")
        if should_stop:
            break

    if best_state is None:
        raise RuntimeError("Training produced no checkpoint")
    model.load_state_dict(best_state)
    final_metrics, prediction_rows = evaluate(model, dev_loader, device, labels, reasons)
    elapsed = time.time() - started
    metadata = {
        "architecture": "constraint-aware multi-task Chinese pair cross-encoder",
        "model_source": args.model_source,
        "stage": args.stage,
        "seed": args.seed,
        "best_epoch": best_epoch,
        "elapsed_seconds": elapsed,
        "parameter_info": parameter_info,
        "config": config,
        "history": history,
        "dev_metrics": final_metrics,
        "data_boundary": "synthetic same-generator dev; not an independent real-world test",
    }
    write_json(output_dir / "metrics.json", metadata)
    torch.save(
        {
            "state_dict": best_state,
            "metadata": metadata,
            "labels": labels,
            "reasons": reasons,
        },
        output_dir / "model.pt",
    )
    tokenizer.save_pretrained(output_dir / "tokenizer")
    model.encoder.config.save_pretrained(output_dir / "encoder_config")
    with (output_dir / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in prediction_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"Completed {args.stage} seed={args.seed}: raw macro-F1={final_metrics['raw']['macro_f1']:.4f}, "
        f"false-reuse={final_metrics['raw']['false_reuse_rate']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
