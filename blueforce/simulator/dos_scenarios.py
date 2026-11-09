"""Bounded synthetic availability and resource-stress scenario generators."""

from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

from blueforce.simulator.resource_model import resource_snapshot


def events(scenario: str, steps: int, rng: random.Random) -> Iterator[dict[str, Any]]:
    slots, requests, service_up = 8, 0, True
    for step in range(steps):
        if scenario == "connection_exhaustion":
            demand = rng.randint(1, 4)
            slots = max(0, slots - demand + rng.randint(0, 2))
            yield {
                "type": scenario, "severity": "HIGH" if slots <= 1 else "INFORMATIONAL",
                "message": f"Synthetic demand={demand}; virtual free slots={slots}/8",
                "data": {"demand": demand, "free_slots": slots},
            }
        elif scenario == "resource_exhaustion":
            resource = resource_snapshot(step, rng)
            cpu, memory = resource["simulated_cpu"], resource["simulated_memory"]
            severity = "HIGH" if max(cpu, memory) >= 85 else "INFORMATIONAL"
            yield {"type": scenario, "severity": severity,
                   "message": f"SIMULATED resource use: CPU {cpu}%, memory {memory}%",
                   "data": {"simulated_cpu": cpu, "simulated_memory": memory}}
        elif scenario == "availability_degradation":
            available = rng.random() > min(0.8, 0.1 + step * 0.12)
            yield {"type": scenario,
                   "severity": "MEDIUM" if not available else "INFORMATIONAL",
                   "message": "Virtual service available" if available else "Simulated virtual request failed",
                   "data": {"available": available}}
        elif scenario == "repeated_request_anomaly":
            requests += rng.randint(1, 5) if step == 0 else rng.randint(1, 14)
            anomaly = requests > 10
            yield {"type": scenario, "severity": "HIGH" if anomaly else "INFORMATIONAL",
                   "message": f"Synthetic request count={requests}; baseline threshold=10",
                   "data": {"requests": requests, "baseline": 10, "anomaly": anomaly}}
        elif scenario == "service_disruption":
            if step == max(1, steps // 3):
                service_up = False
            if step == max(2, (2 * steps) // 3):
                service_up = True
            yield {"type": scenario,
                   "severity": "HIGH" if not service_up else "INFORMATIONAL",
                   "message": "Virtual service operational" if service_up else "Simulated service outage",
                   "data": {"service_up": service_up, "elapsed_step": step}}
        else:
            raise ValueError(f"Unknown simulation scenario: {scenario}")
