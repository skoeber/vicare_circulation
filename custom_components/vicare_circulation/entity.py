"""Shared ViCare Circulation entity base."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ViCareCirculationCoordinator


class ViCareCirculationEntity(CoordinatorEntity[ViCareCirculationCoordinator]):
    """Base entity associated with one Viessmann heating device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ViCareCirculationCoordinator, entry_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        target = coordinator.target
        identifier = f"{target.gateway_serial}_{target.device_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer="Viessmann",
            model=target.model,
            name="Viessmann Warmwasser-Zirkulation",
            serial_number=target.device_serial,
        )
        self._entry_id = entry_id
