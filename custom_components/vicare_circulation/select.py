"""Schedule preset select for ViCare Circulation."""

import logging
from copy import deepcopy

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ViCareCirculationConfigEntry
from .api import ViessmannApiError
from .const import DOMAIN, PRESET_OPTIONS, PRESETS, SCHEDULE_TO_PRESET
from .entity import ViCareCirculationEntity
from .schedule import detect_schedule

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViCareCirculationConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the schedule select."""
    async_add_entities([CirculationScheduleSelect(entry.runtime_data, entry.entry_id)])


class CirculationScheduleSelect(ViCareCirculationEntity, SelectEntity):
    """Select one of the fixed circulation schedule presets."""

    _attr_translation_key = "schedule"
    _attr_icon = "mdi:calendar-clock"
    _attr_options = PRESET_OPTIONS

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_schedule"

    @property
    def current_option(self) -> str | None:
        """Return the preset matching the schedule read from Viessmann."""
        if self.coordinator.data is None:
            return None
        return SCHEDULE_TO_PRESET.get(detect_schedule(self.coordinator.data.schedule))

    @property
    def available(self) -> bool:
        """Return whether schedule selection is available."""
        data = self.coordinator.data
        return bool(
            super().available
            and data
            and data.schedule_feature_enabled
            and data.schedule_feature_ready
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose whether a known or custom plan was detected."""
        state = (
            detect_schedule(self.coordinator.data.schedule)
            if self.coordinator.data
            else "unknown"
        )
        return {"detected_schedule": state}

    async def async_select_option(self, option: str) -> None:
        """Write the selected complete schedule and verify it by reading back."""
        if option not in PRESETS:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_preset",
                translation_placeholders={"preset": option},
            )
        try:
            await self.coordinator.async_write_schedule(deepcopy(PRESETS[option]))
        except (ViessmannApiError, ConfigEntryAuthFailed) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="schedule_write_failed",
                translation_placeholders={"preset": option},
            ) from err
        _LOGGER.info("Activated circulation schedule preset %s", option)
