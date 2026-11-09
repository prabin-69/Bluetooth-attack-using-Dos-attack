"""Virtual-device construction and synthetic activity recording."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from blueforce.models import DeviceType, VirtualDevice


def create_virtual_device(lab_id: str, name: str, device_type: str,
                          **properties: Any) -> VirtualDevice:
    try:
        kind = DeviceType(device_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported device type: {device_type}") from exc
    return VirtualDevice(name=name, device_type=kind, lab_id=lab_id, **properties)


def record_activity(device: VirtualDevice, event: str,
                    details: dict[str, Any] | None = None) -> None:
    if not event.strip():
        raise ValueError("Virtual activity description cannot be empty.")
    device.history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "event": event,
        "details": details or {},
    })
