"""Pump status binary sensor for ViCare Circulation."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ViCareCirculationConfigEntry
from .entity import ViCareCirculationEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViCareCirculationConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the pump status sensor."""
    async_add_entities(
        [CirculationPumpBinarySensor(entry.runtime_data, entry.entry_id)]
    )


class CirculationPumpBinarySensor(ViCareCirculationEntity, BinarySensorEntity):
    """Expose the physical pump status reported by Viessmann."""

    _attr_translation_key = "pump_active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_pump_active"

    @property
    def is_on(self) -> bool | None:
        """Return the reported pump state."""
        if self.coordinator.data is None:
            return None
        status = self.coordinator.data.pump_status
        if status == "on":
            return True
        if status == "off":
            return False
        return None

    @property
    def available(self) -> bool:
        """Return whether the pump status feature is available."""
        data = self.coordinator.data
        return bool(
            super().available
            and data
            and data.pump_feature_enabled
            and data.pump_feature_ready
        )
