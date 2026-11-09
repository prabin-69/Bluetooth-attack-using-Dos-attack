"""Local read-only audit summary; does not infer unavailable security settings."""

from __future__ import annotations

from typing import Any


def audit() -> dict[str, Any]:
    from blueforce.bluetooth.adapter_info import inspect_adapters

    inventory = inspect_adapters()
    return {
        "adapter_inventory": inventory,
        "pairing_security": "UNKNOWN — not exposed by the read-only inventory query",
        "discoverability": "UNKNOWN — not exposed by the read-only inventory query",
        "encryption": "UNKNOWN — connection encryption is not exposed here",
        "assessment": "No security weakness inferred from unavailable operating-system data.",
        "recommendations": [
            "Use authenticated pairing and remove devices you no longer use.",
            "Keep Bluetooth off or non-discoverable when not needed.",
            "Install operating-system and adapter firmware security updates.",
        ],
    }
