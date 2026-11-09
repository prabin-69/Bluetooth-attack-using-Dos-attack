"""Read-only aggregate application state for dashboards and health checks."""

from __future__ import annotations

from typing import Any

from blueforce.database.repository import Repository


class StateManager:
    def __init__(self, repository: Repository):
        self.repository = repository

    def snapshot(self) -> dict[str, Any]:
        return {
            "laboratories": len(self.repository.labs()),
            "virtual_devices": self.repository.connection.execute(
                "SELECT COUNT(*) FROM virtual_devices"
            ).fetchone()[0],
            "running_simulations": self.repository.connection.execute(
                "SELECT COUNT(*) FROM simulation_sessions WHERE status='RUNNING'"
            ).fetchone()[0],
            "unacknowledged_alerts": self.repository.connection.execute(
                "SELECT COUNT(*) FROM security_alerts WHERE acknowledged=0"
            ).fetchone()[0],
            "data_scope": "Local BLUEFORCE X database only",
        }
