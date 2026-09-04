"""Test bootstrap without requiring a complete Home Assistant installation."""

import sys
from enum import StrEnum
from pathlib import Path
from types import ModuleType


class Platform(StrEnum):
    """Minimal platform enum used while importing integration constants."""

    BINARY_SENSOR = "binary_sensor"
    SELECT = "select"
    SENSOR = "sensor"


ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "vicare_circulation"

# Loading a submodule normally executes the integration's __init__.py, which requires
# Home Assistant. Use a namespace package so pure schedule and API tests stay small.
custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
integration = ModuleType("custom_components.vicare_circulation")
integration.__path__ = [str(PACKAGE_PATH)]
homeassistant = ModuleType("homeassistant")
homeassistant_const = ModuleType("homeassistant.const")
homeassistant_const.Platform = Platform
homeassistant_config_entries = ModuleType("homeassistant.config_entries")
homeassistant_core = ModuleType("homeassistant.core")
homeassistant_exceptions = ModuleType("homeassistant.exceptions")
homeassistant_helpers = ModuleType("homeassistant.helpers")
homeassistant_update_coordinator = ModuleType(
    "homeassistant.helpers.update_coordinator"
)


class ConfigEntry:
    """Minimal config entry type stub."""


class HomeAssistant:
    """Minimal Home Assistant type stub."""


class ConfigEntryAuthFailed(Exception):
    """Authentication failure stub."""


class UpdateFailed(Exception):
    """Coordinator update failure stub."""


class DataUpdateCoordinator[DataT]:
    """Minimal coordinator implementation for behavioral unit tests."""

    def __init__(self, hass, logger, *, config_entry, name, update_interval) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self.data = None
        self.last_update_success = True
        self.refresh_requests = 0

    def async_set_updated_data(self, data) -> None:
        self.data = data

    async def async_request_refresh(self) -> None:
        self.refresh_requests += 1
        self.async_set_updated_data(await self._async_update_data())


homeassistant_config_entries.ConfigEntry = ConfigEntry
homeassistant_core.HomeAssistant = HomeAssistant
homeassistant_exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
homeassistant_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
homeassistant_update_coordinator.UpdateFailed = UpdateFailed

sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.vicare_circulation", integration)
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.const", homeassistant_const)
sys.modules.setdefault("homeassistant.config_entries", homeassistant_config_entries)
sys.modules.setdefault("homeassistant.core", homeassistant_core)
sys.modules.setdefault("homeassistant.exceptions", homeassistant_exceptions)
sys.modules.setdefault("homeassistant.helpers", homeassistant_helpers)
sys.modules.setdefault(
    "homeassistant.helpers.update_coordinator", homeassistant_update_coordinator
)
