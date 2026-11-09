"""Clearly separated synthetic lab metrics and actual host measurements."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from blueforce.database.repository import Repository


def lab_metrics(repository: Repository, lab_id: str) -> dict[str, Any]:
    lab = repository.lab(lab_id)
    if lab is None:
        raise ValueError(f"Lab not found: {lab_id}")
    devices = repository.devices(lab["id"])
    sessions = repository.sessions(lab["id"])
    alerts = repository.alerts(lab["id"])
    events: list[dict[str, Any]] = []
    if sessions:
        rows = repository.connection.execute(
            """SELECT event_type,severity,data_json FROM simulation_events
               WHERE session_id=? ORDER BY id""", (sessions[0]["id"],)
        )
        events = [dict(row) for row in rows]
    data = [json.loads(row["data_json"]) for row in events]
    summary = json.loads(sessions[0]["summary_json"]) if sessions else {}
    resource = [item for item in data if "simulated_cpu" in item]
    availability = [item for item in data if "available" in item]
    available = sum(bool(item["available"]) for item in availability)
    device_states = Counter("connected" if row["connected"] else "disconnected"
                            for row in devices)
    severity_counts = Counter(row["severity"] for row in alerts)
    graph = "No simulated resource samples."
    if resource:
        cpu = " ".join("#" * (item["simulated_cpu"] // 10) or "." for item in resource)
        memory = " ".join("#" * (item["simulated_memory"] // 10) or "." for item in resource)
        graph = f"CPU  [0-100%] {cpu}\nMEM  [0-100%] {memory}"
    return {
        "lab": lab["name"],
        "virtual_device_count": len(devices),
        "active_virtual_connections": sum(int(row["connected"]) for row in devices),
        "virtual_device_state_distribution": dict(device_states),
        "synthetic_event_count_latest_session": len(events),
        "simulated_events_per_second": summary.get("events_per_second"),
        "alert_count": len(alerts),
        "threat_severity_distribution": dict(severity_counts),
        "incident_count": len(repository.incidents(lab["id"])),
        "simulated_cpu_percent": resource[-1]["simulated_cpu"] if resource else None,
        "simulated_memory_percent": resource[-1]["simulated_memory"] if resource else None,
        "simulated_resource_graph_ascii": graph,
        "simulated_availability_percent": (
            round(100 * available / len(availability), 1) if availability else None
        ),
        "measurements": "SIMULATED values are virtual-model data, not host utilization.",
    }


def actual_host_metrics() -> dict[str, Any]:
    """Return real host values with explicit provenance; never mix with lab metrics."""
    try:
        import psutil
    except ImportError:
        return {"source": "ACTUAL HOST", "available": False,
                "note": "Install psutil to sample actual host CPU and memory."}
    return {
        "source": "ACTUAL HOST",
        "available": True,
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "note": "These are actual computer measurements, not simulated Bluetooth values.",
    }
