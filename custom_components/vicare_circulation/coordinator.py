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
from .const import (
    DOMAIN,
    SCHEDULE_FOLLOW_UP_DELAY,
    SCHEDULE_VERIFY_DELAYS,
    UPDATE_INTERVAL,
)
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
        self._pending_schedule: Schedule | None = None
        self._follow_up_task: asyncio.Task[None] | None = None
        config_entry.async_on_unload(self._cancel_follow_up_refresh)

    async def _async_update_data(self) -> CirculationData:
        """Fetch the current schedule and pump state."""
        try:
            data = await self.api.async_get_circulation_data(self.target)
        except ViessmannApiAuthenticationError as err:
            self.config_entry.async_start_reauth_if_available(self.hass)
            raise ConfigEntryAuthFailed from err
        except ViessmannApiError as err:
            raise UpdateFailed(str(err)) from err

        if self._schedules_match(data.schedule, self._pending_schedule):
            _LOGGER.info("Viessmann confirmed the pending circulation schedule")
            self._pending_schedule = None
            self._cancel_follow_up_refresh()
        return data

    async def async_write_schedule(self, schedule: Schedule) -> bool:
        """Write a schedule and return whether Viessmann confirmed it promptly."""
        async with self.write_lock:
            try:
                await self.api.async_set_schedule(self.target, schedule)
            except ViessmannApiAuthenticationError as err:
                self.config_entry.async_start_reauth_if_available(self.hass)
                raise ConfigEntryAuthFailed from err

            self._cancel_follow_up_refresh()
            self._pending_schedule = schedule
            for delay in SCHEDULE_VERIFY_DELAYS:
                if delay:
                    await asyncio.sleep(delay)
                try:
                    data = await self.api.async_get_circulation_data(self.target)
                except ViessmannApiAuthenticationError as err:
                    self.config_entry.async_start_reauth_if_available(self.hass)
                    raise ConfigEntryAuthFailed from err

                self.async_set_updated_data(data)
                if self._schedules_match(data.schedule, schedule):
                    self._pending_schedule = None
                    self._cancel_follow_up_refresh()
                    return True

            self._schedule_follow_up_refresh()
            return False

    def _schedule_follow_up_refresh(self) -> None:
        """Schedule one later refresh without blocking the service call."""
        self._cancel_follow_up_refresh()
        self._follow_up_task = self.hass.async_create_task(
            self._async_follow_up_refresh(),
            f"{DOMAIN} schedule confirmation refresh",
        )

    async def _async_follow_up_refresh(self) -> None:
        """Refresh after Viessmann has had more time to publish the new plan."""
        task = asyncio.current_task()
        try:
            await asyncio.sleep(SCHEDULE_FOLLOW_UP_DELAY)
            await self.async_request_refresh()
        finally:
            if self._follow_up_task is task:
                self._follow_up_task = None

    def _cancel_follow_up_refresh(self) -> None:
        """Cancel an obsolete confirmation refresh."""
        task = self._follow_up_task
        self._follow_up_task = None
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()

    @staticmethod
    def _schedules_match(actual: Schedule | None, expected: Schedule | None) -> bool:
        """Compare schedules without treating two missing schedules as confirmed."""
        if actual is None or expected is None:
            return False
        return normalize_schedule(actual) == normalize_schedule(expected)
