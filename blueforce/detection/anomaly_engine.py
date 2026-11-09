"""Explainable defensive rules for synthetic lab events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from blueforce.detection.detection_rules import EventCorrelator, StatisticalAnomalyDetector
from blueforce.models import Severity


class AnomalyEngine:
    def __init__(self, request_threshold: int = 10, resource_threshold: int = 85,
                 z_threshold: float = 3.0, correlation_threshold: int = 3):
        if request_threshold < 1 or not 1 <= resource_threshold <= 100:
            raise ValueError("Detection thresholds are outside supported limits.")
        self.request_threshold = request_threshold
        self.resource_threshold = resource_threshold
        self.z_threshold = z_threshold
        self.correlation_threshold = correlation_threshold
        self.statistics = StatisticalAnomalyDetector(z_threshold=z_threshold)
        self.correlator = EventCorrelator(threshold=correlation_threshold)

    def new_session(self) -> AnomalyEngine:
        """Create an independent baseline/correlation context for one lab run."""
        return AnomalyEngine(
            request_threshold=self.request_threshold,
            resource_threshold=self.resource_threshold,
            z_threshold=self.z_threshold,
            correlation_threshold=self.correlation_threshold,
        )

    def inspect(self, event: dict[str, Any]) -> dict[str, Any] | None:
        data, rule, explanation, severity, confidence = event.get("data", {}), None, None, None, 0.0
        statistical = self.statistics.inspect(event)
        if event["type"] == "repeated_request_anomaly" and data.get("requests", 0) > self.request_threshold:
            rule, explanation, severity, confidence = (
                "request-rate-deviation",
                f"Request count {data['requests']} exceeded configured baseline {self.request_threshold}.",
                Severity.HIGH.value, 0.94,
            )
        elif event["type"] == "resource_exhaustion" and max(
            data.get("simulated_cpu", 0), data.get("simulated_memory", 0)
        ) >= self.resource_threshold:
            rule, explanation, severity, confidence = (
                "simulated-resource-saturation",
                f"Synthetic CPU or memory utilization reached {self.resource_threshold}% or higher.",
                Severity.HIGH.value, 0.91,
            )
        elif event["type"] == "connection_exhaustion" and data.get("free_slots", 8) <= 1:
            rule, explanation, severity, confidence = (
                "virtual-connection-saturation",
                "The isolated lab model has at most one available virtual connection slot.",
                Severity.MEDIUM.value, 0.88,
            )
        elif event["type"] == "availability_degradation" and not data.get("available", True):
            rule, explanation, severity, confidence = (
                "virtual-availability-degradation",
                "A synthetic service availability check failed inside the virtual lab.",
                Severity.MEDIUM.value, 0.90,
            )
        elif event["type"] == "service_disruption" and not data.get("service_up", True):
            rule, explanation, severity, confidence = (
                "simulated-service-outage",
                "The scenario intentionally marked the virtual service unavailable.",
                Severity.HIGH.value, 0.99,
            )
        if rule is None and statistical is None:
            return None
        if rule is None:
            rule = f"statistical-{statistical['metric']}-deviation"
            explanation = (
                f"{statistical['metric']}={statistical['value']} is "
                f"{statistical['z_score']} standard deviations from the observed baseline "
                f"mean {statistical['baseline_mean']}."
            )
            severity = Severity.MEDIUM.value
            confidence = min(0.99, 0.75 + statistical["z_score"] / 100)
        elif statistical:
            explanation += (
                f" Statistical corroboration: {statistical['metric']} z-score "
                f"{statistical['z_score']} against the recent baseline."
            )
            confidence = min(0.99, confidence + 0.03)
        occurrences = self.correlator.observe(rule)
        if occurrences >= self.correlator.threshold:
            explanation += f" Correlated with {occurrences} recent occurrences of this rule."
            severity = (
                Severity.CRITICAL.value if severity == Severity.HIGH.value
                else Severity.HIGH.value
            )
            confidence = min(0.99, confidence + 0.04)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "rule": rule, "severity": severity, "confidence": confidence,
            "explanation": explanation,
            "data": {**data, **({"statistical_evidence": statistical}
                                  if statistical else {}),
                     "correlated_occurrences": occurrences},
        }
