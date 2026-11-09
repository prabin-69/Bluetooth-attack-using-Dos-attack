"""Incident workflow facade over repository transactions."""

from __future__ import annotations

from blueforce.database.repository import Repository


class IncidentManager:
    def __init__(self, repository: Repository):
        self.repository = repository

    def create(self, lab_id: str, title: str, classification: str) -> str:
        if not title.strip() or len(title) > 160:
            raise ValueError("Incident title must contain 1–160 characters.")
        if self.repository.lab(lab_id) is None:
            raise ValueError(f"Lab not found: {lab_id}")
        return self.repository.create_incident(lab_id, title, classification)

    def transition(self, incident_id: str, status: str, note: str | None = None) -> bool:
        return self.repository.set_incident(incident_id, status, note)

    def list(self, lab_id: str | None = None):
        return self.repository.incidents(lab_id)
