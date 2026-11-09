"""Virtual lab and device lifecycle helpers."""

from __future__ import annotations

from blueforce.database.repository import Repository
from blueforce.models import VirtualDevice
from blueforce.simulator.virtual_device import create_virtual_device


class VirtualLab:
    def __init__(self, repository: Repository, lab_id: str):
        lab = repository.lab(lab_id)
        if lab is None:
            raise ValueError(f"Lab not found: {lab_id}")
        self.repository = repository
        self.lab_id = lab["id"]
        self.name = lab["name"]

    def add_device(self, name: str, device_type: str, **properties: object) -> VirtualDevice:
        device = create_virtual_device(self.lab_id, name, device_type, **properties)
        self.repository.add_device(device)
        return device

    def remove_device(self, identifier: str) -> bool:
        return self.repository.remove_device(self.lab_id, identifier)

    def devices(self):
        return self.repository.devices(self.lab_id)
