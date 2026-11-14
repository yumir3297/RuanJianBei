from __future__ import annotations

from typing import Any

import torch
from torch import nn
from transformers import AutoConfig, AutoModel


class GuideMatchModel(nn.Module):
    """Shared text encoder with main-label and auxiliary-reason heads."""

    def __init__(
        self,
        model_source: str,
        num_labels: int,
        num_reasons: int,
        dropout: float,
        load_pretrained: bool = True,
    ) -> None:
        super().__init__()
        if load_pretrained:
            self.encoder = AutoModel.from_pretrained(model_source)
        else:
            self.encoder = AutoModel.from_config(AutoConfig.from_pretrained(model_source))
        hidden_size = int(self.encoder.config.hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.label_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_labels),
        )
        self.reason_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_reasons),
        )

    def forward(self, **tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        output = self.encoder(**tokens)
        # BGE embedding checkpoints are trained to expose the semantic vector at
        # the first token; using it also avoids depending on an optional pooler.
        pooled = output.last_hidden_state[:, 0]
        pooled = self.dropout(pooled)
        return self.label_head(pooled), self.reason_head(pooled)

    def configure_stage(self, stage: str) -> dict[str, Any]:
        for parameter in self.encoder.parameters():
            parameter.requires_grad = False

        if stage == "frozen":
            pass
        elif stage == "last_layer":
            layers = _find_transformer_layers(self.encoder)
            for parameter in layers[-1].parameters():
                parameter.requires_grad = True
        else:
            raise ValueError(f"Unsupported training stage: {stage}")

        trainable = sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)
        total = sum(parameter.numel() for parameter in self.parameters())
        return {"stage": stage, "trainable_parameters": trainable, "total_parameters": total}


def _find_transformer_layers(encoder: nn.Module) -> Any:
    candidates = [
        getattr(getattr(encoder, "encoder", None), "layer", None),
        getattr(getattr(getattr(encoder, "bert", None), "encoder", None), "layer", None),
        getattr(getattr(getattr(encoder, "roberta", None), "encoder", None), "layer", None),
    ]
    for layers in candidates:
        if layers is not None and len(layers):
            return layers
    raise RuntimeError("Cannot locate Transformer blocks for last_layer stage")
