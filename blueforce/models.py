"""Validated domain types shared across application layers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceType(StrEnum):
    SMARTPHONE = "smartphone"
    LAPTOP = "laptop"
    HEADPHONES = "headphones"
    SMARTWATCH = "smartwatch"
    IOT_SENSOR = "iot_sensor"
    SPEAKER = "bluetooth_speaker"
    BLE_PERIPHERAL = "ble_peripheral"


class Severity(StrEnum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


class VirtualDevice(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    name: str
    device_type: DeviceType
    lab_id: str
    identifier: str = Field(default_factory=lambda: f"SIM-{uuid4().hex[:12].upper()}")
    signal_dbm: int = Field(default=-55, ge=-100, le=0)
    connected: bool = False
    pairing: str = "secure"
    discoverable: bool = False
    encrypted: bool = True
    battery: int = Field(default=100, ge=0, le=100)
    risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    history: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip() or len(value) > 80:
            raise ValueError("Device name cannot be empty.")
        return value.strip()

    @field_validator("pairing")
    @classmethod
    def validate_pairing(cls, value: str) -> str:
        if value not in {"secure", "legacy", "unknown"}:
            raise ValueError("Pairing must be secure, legacy, or unknown.")
        return value
