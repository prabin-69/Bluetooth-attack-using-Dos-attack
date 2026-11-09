"""Seeded virtual CPU and memory utilization model."""

from __future__ import annotations

import random


def resource_snapshot(step: int, rng: random.Random) -> dict[str, int]:
    if step < 0:
        raise ValueError("Resource-model step cannot be negative.")
    return {
        "simulated_cpu": min(100, max(5, 25 + step * 6 + rng.randint(-8, 8))),
        "simulated_memory": min(100, max(10, 30 + step * 4 + rng.randint(-6, 6))),
    }
