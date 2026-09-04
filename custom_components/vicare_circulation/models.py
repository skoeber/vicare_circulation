"""Data models for ViCare Circulation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

Schedule = dict[str, list[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class Target:
    """A Viessmann heating device target."""

    installation_id: str
    gateway_serial: str
    device_id: str
    device_serial: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class CirculationData:
    """Current circulation state returned by Viessmann."""

    schedule: Schedule | None
    schedule_active: bool | None
    pump_status: str | None
    schedule_feature_enabled: bool
    schedule_feature_ready: bool
    pump_feature_enabled: bool
    pump_feature_ready: bool
    last_successful_update: datetime
