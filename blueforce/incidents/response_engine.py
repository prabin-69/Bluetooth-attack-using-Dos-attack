"""Non-invasive incident response rehearsal inside the virtual lab."""

from __future__ import annotations

from blueforce.database.repository import Repository


class ResponseEngine:
    def __init__(self, repository: Repository):
        self.repository = repository

    def rehearse_recovery(self, incident_id: str) -> dict[str, str]:
        incident = next(
            (row for row in self.repository.incidents()
             if row["id"] == incident_id), None
        )
        if incident is None:
            raise ValueError(f"Incident not found: {incident_id}")
        if incident["status"] not in {"OPEN", "INVESTIGATING", "CONTAINED"}:
            raise ValueError("Only unresolved incidents can enter simulated recovery.")
        self.repository.set_incident(
            incident_id, "CONTAINED", "SIMULATED: recovery rehearsal started."
        )
        self.repository.set_incident(
            incident_id, "RESOLVED", "SIMULATED: virtual service recovery completed."
        )
        return {"incident_id": incident_id, "status": "RESOLVED",
                "result": "Virtual-only recovery rehearsal; no host service was changed."}
