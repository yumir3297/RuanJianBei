from __future__ import annotations

import math


def _nearest_rank(values: list[float], percentile: float) -> float:
    index = max(0, math.ceil(percentile * len(values)) - 1)
    return values[index]


def summarize_latency(values_ms: list[int | float]) -> dict[str, int | float]:
    if not values_ms:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }
    sorted_values = sorted(float(value) for value in values_ms)
    return {
        "count": len(sorted_values),
        "avg_ms": sum(sorted_values) / len(sorted_values),
        "p50_ms": _nearest_rank(sorted_values, 0.50),
        "p95_ms": _nearest_rank(sorted_values, 0.95),
        "min_ms": sorted_values[0],
        "max_ms": sorted_values[-1],
    }
