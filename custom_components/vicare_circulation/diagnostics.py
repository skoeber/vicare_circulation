"""Sanitized diagnostics for ViCare Circulation."""

from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant

from . import ViCareCirculationConfigEntry
from .schedule import detect_schedule


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ViCareCirculationConfigEntry
) -> dict[str, Any]:
    """Return diagnostics without OAuth data or equipment identifiers."""
    coordinator = entry.runtime_data
    data = coordinator.data
    if data is None:
        return {"last_update_success": coordinator.last_update_success}
    return {
        "last_update_success": coordinator.last_update_success,
        "detected_schedule": detect_schedule(data.schedule),
        "schedule": deepcopy(data.schedule),
        "schedule_active": data.schedule_active,
        "schedule_feature_enabled": data.schedule_feature_enabled,
        "schedule_feature_ready": data.schedule_feature_ready,
        "pump_status": data.pump_status,
        "pump_feature_enabled": data.pump_feature_enabled,
        "pump_feature_ready": data.pump_feature_ready,
        "last_successful_update": data.last_successful_update.isoformat(),
    }
