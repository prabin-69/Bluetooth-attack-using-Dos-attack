"""Validated persistence-facing event and alert records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from blueforce.models import Severity


class SimulationEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    event_type: str
    severity: Severity
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type", "message")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Event type and message cannot be empty.")
        return value


class SecurityAlertRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    rule: str
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    explanation: str
    data: dict[str, Any] = Field(default_factory=dict)
