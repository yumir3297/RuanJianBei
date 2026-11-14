"""Optional local GuideMatch inference for FAQ candidates."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import logging
import threading
import re

logger = logging.getLogger(__name__)


def structured_hard_rule(left_meta, right_meta):
    for key in ("poi_id", "target_id", "queried_date"):
        left = str((left_meta or {}).get(key) or "").strip()
        right = str((right_meta or {}).get(key) or "").strip()
        if left and right and left != right:
            return "distinct"
        if bool(left) != bool(right):
            return "clarify"
    return None


def text_date_conflict(query, candidate):
    pattern = r"(?:今天|明天|后天|昨天|前天|\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)"
    left, right = set(re.findall(pattern, query)), set(re.findall(pattern, candidate))
    return bool((left or right) and left != right)


class GuideMatchGate:
    def __init__(self, model_dir: str, device: str = "cuda", reuse_threshold: float = 0.70, min_confidence: float = 0.40):
        import torch
        from torch import nn
        from transformers import AutoConfig, AutoModel, AutoTokenizer

        if device not in {"cpu", "cuda"}:
            raise ValueError("GuideMatch device must be cpu or cuda")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("GuideMatch CUDA unavailable; choose CPU explicitly for local testing")
        self.device = device
        self.reuse_threshold = reuse_threshold
        self.min_confidence = min_confidence

        root = Path(model_dir)
        config = AutoConfig.from_pretrained(str(root / "encoder_config"), local_files_only=True)

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = AutoModel.from_config(config)
                n = int(config.hidden_size)
                self.label_head = nn.Sequential(nn.Linear(n, n), nn.GELU(), nn.Dropout(0.15), nn.Linear(n, 3))
                self.reason_head = nn.Sequential(nn.Linear(n, n // 2), nn.GELU(), nn.Dropout(0.15), nn.Linear(n // 2, 6))

            def forward(self, **tokens):
                pooled = self.encoder(**tokens).last_hidden_state[:, 0]
                return self.label_head(pooled)

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(str(root / "tokenizer"), local_files_only=True)
        self.model = Model()
        checkpoint = torch.load(root / "model.pt", map_location="cpu", weights_only=True)
        self.model.load_state_dict(checkpoint["state_dict"], strict=True)
        self.model.to(device)
        self.model.eval()
        self.lock = threading.Lock()

    def decide(self, query: str, candidate: str, left_meta=None, right_meta=None) -> str:
        hard = structured_hard_rule(left_meta, right_meta)
        if hard:
            return hard
        if text_date_conflict(query, candidate):
            return "clarify"
        tokens = self.tokenizer([query], [candidate], padding=True, truncation=True, max_length=128, return_tensors="pt")
        tokens = {key: value.to(self.device) for key, value in tokens.items()}
        with self.lock, self.torch.inference_mode():
            probabilities = self.model(**tokens).softmax(dim=-1)[0].tolist()
        winner = max(range(3), key=probabilities.__getitem__)
        if winner == 0:
            if probabilities[0] >= self.reuse_threshold:
                return "reuse"
            alternative = max((1, 2), key=probabilities.__getitem__)
            return ("reuse", "distinct", "clarify")[alternative] if probabilities[alternative] >= self.min_confidence else "clarify"
        return ("reuse", "distinct", "clarify")[winner] if probabilities[winner] >= self.min_confidence else "clarify"


@lru_cache(maxsize=1)
def load_gate(model_dir: str, device: str = "cuda", reuse_threshold: float = 0.70, min_confidence: float = 0.40):
    try:
        return GuideMatchGate(model_dir, device, reuse_threshold, min_confidence)
    except Exception:
        logger.exception("GuideMatch unavailable; non-exact FAQ reuse is disabled")
        return UnavailableGate()


class UnavailableGate:
    def decide(self, query, candidate):
        return "clarify"
