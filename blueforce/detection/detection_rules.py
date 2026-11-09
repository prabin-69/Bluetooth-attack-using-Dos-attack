"""Bounded statistical baselines and recent-event correlation."""

from __future__ import annotations

from collections import defaultdict, deque
from math import sqrt
from typing import Any


class StatisticalAnomalyDetector:
    def __init__(self, minimum_samples: int = 3, z_threshold: float = 3.0):
        if minimum_samples < 2 or z_threshold <= 0:
            raise ValueError("Statistical detector parameters must be positive.")
        self.minimum_samples = minimum_samples
        self.z_threshold = z_threshold
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=64))

    def inspect(self, event: dict[str, Any]) -> dict[str, Any] | None:
        numeric = {
            key: value for key, value in event.get("data", {}).items()
            if key in {"requests", "simulated_cpu", "simulated_memory", "free_slots"}
            and isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        findings = []
        for key, value in numeric.items():
            samples = self._samples[key]
            if len(samples) >= self.minimum_samples:
                mean = sum(samples) / len(samples)
                variance = sum((item - mean) ** 2 for item in samples) / len(samples)
                deviation = sqrt(variance)
                z_score = abs(value - mean) / deviation if deviation else 0
                if z_score >= self.z_threshold:
                    findings.append({"metric": key, "value": value,
                                     "baseline_mean": round(mean, 3),
                                     "z_score": round(z_score, 3)})
            samples.append(float(value))
        return findings[0] if findings else None


class EventCorrelator:
    """Track only recent matching rules; memory use is fixed and bounded."""

    def __init__(self, window: int = 20, threshold: int = 3):
        if window < 1 or threshold < 2 or threshold > window:
            raise ValueError("Correlation window and threshold are invalid.")
        self.threshold = threshold
        self._recent: deque[str] = deque(maxlen=window)

    def observe(self, rule: str) -> int:
        self._recent.append(rule)
        return sum(item == rule for item in self._recent)
