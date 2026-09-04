"""Schedule status and diagnostics sensors for ViCare Circulation."""

from copy import deepcopy

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ViCareCirculationConfigEntry
from .const import SCHEDULE_TO_PRESET
from .entity import ViCareCirculationEntity
from .schedule import detect_schedule

_STATUS_NAMES = {
    "custom": "Benutzerdefiniert",
    "unknown": "Unbekannt",
    **SCHEDULE_TO_PRESET,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViCareCirculationConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up circulation sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            CirculationScheduleStatusSensor(coordinator, entry.entry_id),
            CirculationScheduleDiagnosticSensor(coordinator, entry.entry_id),
        ]
    )


class CirculationScheduleStatusSensor(ViCareCirculationEntity, SensorEntity):
    """Show which preset matches the current Viessmann schedule."""

    _attr_translation_key = "schedule_status"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_schedule_status"

    @property
    def native_value(self) -> str:
        """Return the translated matching status."""
        if self.coordinator.data is None:
            return _STATUS_NAMES["unknown"]
        return _STATUS_NAMES[detect_schedule(self.coordinator.data.schedule)]

    @property
    def available(self) -> bool:
        """Return whether the schedule feature is available."""
        data = self.coordinator.data
        return bool(
            super().available
            and data
            and data.schedule_feature_enabled
            and data.schedule_feature_ready
        )


class CirculationScheduleDiagnosticSensor(ViCareCirculationEntity, SensorEntity):
    """Expose the sanitized current API schedule for diagnostics."""

    _attr_translation_key = "api_schedule"
    _attr_icon = "mdi:code-json"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_api_schedule"

    @property
    def native_value(self) -> str:
        """Return a short, stable state."""
        return "available"

    @property
    def available(self) -> bool:
        """Return whether schedule diagnostics are available."""
        data = self.coordinator.data
        return bool(super().available and data)

    @property
    def extra_state_attributes(self) -> dict:
        """Return schedule details without installation identifiers or tokens."""
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "schedule": deepcopy(data.schedule),
            "schedule_active": data.schedule_active,
            "feature_enabled": data.schedule_feature_enabled,
            "feature_ready": data.schedule_feature_ready,
            "last_successful_update": data.last_successful_update.isoformat(),
        }
