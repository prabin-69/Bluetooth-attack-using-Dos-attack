"""Read-only Bluetooth adapter discovery on Windows; unknown is not unsafe."""

from __future__ import annotations

import json
import platform
import subprocess


def inspect_adapters() -> dict[str, object]:
    result: dict[str, object] = {
        "platform": platform.platform(), "available": None, "adapters": [],
        "note": "Unknown means the operating system did not expose this information.",
    }
    if platform.system() != "Windows":
        result["note"] = "Read-only adapter inspection is implemented for Windows only."
        return result
    command = (
        "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
        "Select-Object FriendlyName,Status,InstanceId | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["note"] = f"Read-only adapter query unavailable: {exc}"
        return result
    if completed.returncode != 0:
        result["note"] = "Windows did not provide adapter information; state is unknown."
        return result
    try:
        devices = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        result["note"] = "Windows returned unrecognized adapter data; state is unknown."
        return result
    if devices is None:
        devices = []
    elif isinstance(devices, dict):
        devices = [devices]
    elif not isinstance(devices, list):
        result["note"] = "Windows returned an unexpected adapter data shape; state is unknown."
        return result
    adapters = [
        {"name": device.get("FriendlyName", "Unknown"),
         "status": device.get("Status", "Unknown"),
         "instance_id": device.get("InstanceId", "Unknown")}
        for device in devices if isinstance(device, dict)
    ]
    result.update(available=bool(adapters), adapters=adapters)
    return result
