"""Data update coordinator for ViCare Circulation."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ViessmannApiAuthenticationError,
    ViessmannApiClient,
    ViessmannApiError,
)
from .const import DOMAIN, UPDATE_INTERVAL
from .models import CirculationData, Schedule, Target
from .schedule import normalize_schedule

_LOGGER = logging.getLogger(__name__)


class ViCareCirculationCoordinator(DataUpdateCoordinator[CirculationData]):
    """Coordinate Viessmann circulation reads and serialized writes."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: ViessmannApiClient,
        target: Target,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        self.target = target
        self.write_lock = asyncio.Lock()

    async def _async_update_data(self) -> CirculationData:
        """Fetch the current schedule and pump state."""
        try:
            return await self.api.async_get_circulation_data(self.target)
        except ViessmannApiAuthenticationError as err:
            self.config_entry.async_start_reauth_if_available(self.hass)
            raise ConfigEntryAuthFailed from err
        except ViessmannApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_write_schedule(self, schedule: Schedule) -> None:
        """Write and then verify a complete schedule."""
        async with self.write_lock:
            try:
                await self.api.async_set_schedule(self.target, schedule)
                data = await self.api.async_get_circulation_data(self.target)
            except ViessmannApiAuthenticationError as err:
                self.config_entry.async_start_reauth_if_available(self.hass)
                raise ConfigEntryAuthFailed from err
            self.async_set_updated_data(data)
            if normalize_schedule(data.schedule) != normalize_schedule(schedule):
                raise ViessmannApiError(
                    "Viessmann did not confirm the requested circulation schedule"
                )
