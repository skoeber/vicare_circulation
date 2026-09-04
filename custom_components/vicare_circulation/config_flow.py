"""Config flow for ViCare Circulation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .api import (
    ViessmannApiAuthenticationError,
    ViessmannApiClient,
    ViessmannApiError,
    ViessmannApiInvalidDataError,
    ViessmannApiNotSupportedError,
    item_id,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_SERIAL,
    CONF_GATEWAY_SERIAL,
    CONF_INSTALLATION_ID,
    DOMAIN,
    NAME,
)
from .models import Target

_LOGGER = logging.getLogger(__name__)


class _FlowOAuthSession:
    """Use a newly issued token before a config entry exists."""

    def __init__(self, hass: HomeAssistant, token: dict[str, Any]) -> None:
        self._hass = hass
        self._token = token

    async def async_request(self, method: str, url: str, **kwargs: Any):
        """Perform an authenticated request with flow-local token data."""
        return await config_entry_oauth2_flow.async_oauth2_request(
            self._hass, self._token, method, url, **kwargs
        )


class ViCareCirculationConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Configure a Viessmann circulation schedule device."""

    DOMAIN = DOMAIN
    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._oauth_data: dict[str, Any] = {}
        self._api: ViessmannApiClient | None = None
        self._installations: dict[str, dict[str, Any]] = {}
        self._gateways: dict[str, dict[str, Any]] = {}
        self._devices: dict[str, dict[str, Any]] = {}
        self._installation_id: str | None = None
        self._gateway_serial: str | None = None
        self._reconfigure_entry = None
        super().__init__()

    @property
    @override
    def logger(self) -> logging.Logger:
        """Return the flow logger."""
        return _LOGGER

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start OAuth configuration."""
        return await super().async_step_user(user_input)

    @override
    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        """Continue target discovery after OAuth or finish reauthentication."""
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, **data},
            )

        self._oauth_data = data
        self._api = ViessmannApiClient(_FlowOAuthSession(self.hass, data["token"]))
        return await self._async_start_target_discovery()

    async def _async_start_target_discovery(self) -> ConfigFlowResult:
        """Load installations before target selection."""
        if self._api is None:
            return self.async_abort(reason="unknown")
        try:
            installations = await self._api.async_get_installations()
        except ViessmannApiError:
            _LOGGER.exception("Could not discover Viessmann installations")
            return self.async_abort(reason="cannot_connect")

        self._installations = {
            identifier: item
            for item in installations
            if (identifier := item_id(item, "id", "installationId")) is not None
        }
        if not self._installations:
            return self.async_abort(reason="no_installations")
        if len(self._installations) == 1:
            self._installation_id = next(iter(self._installations))
            return await self.async_step_gateway()
        return await self.async_step_installation()

    async def async_step_installation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select one of multiple installations."""
        if user_input is not None:
            self._installation_id = user_input[CONF_INSTALLATION_ID]
            return await self.async_step_gateway()
        return self.async_show_form(
            step_id="installation",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INSTALLATION_ID): vol.In(
                        {
                            key: _item_label(value, key, "description", "name")
                            for key, value in self._installations.items()
                        }
                    )
                }
            ),
        )

    async def async_step_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover and select a gateway."""
        if self._api is None or self._installation_id is None:
            return self.async_abort(reason="unknown")
        if not self._gateways:
            try:
                gateways = await self._api.async_get_gateways(
                    self._installation_id,
                    allow_unassociated=len(self._installations) == 1,
                )
            except ViessmannApiError:
                _LOGGER.exception("Could not discover Viessmann gateways")
                return self.async_abort(reason="cannot_connect")
            self._gateways = {
                identifier: item
                for item in gateways
                if (identifier := item_id(item, "serial", "gatewaySerial", "id"))
                is not None
            }
            if not self._gateways:
                return self.async_abort(reason="no_gateways")

        if user_input is not None:
            self._gateway_serial = user_input[CONF_GATEWAY_SERIAL]
            return await self.async_step_device()
        if len(self._gateways) == 1:
            self._gateway_serial = next(iter(self._gateways))
            return await self.async_step_device()
        return self.async_show_form(
            step_id="gateway",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GATEWAY_SERIAL): vol.In(
                        {
                            key: _item_label(value, key, "type", "model")
                            for key, value in self._gateways.items()
                        }
                    )
                }
            ),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover, validate, and select a heating device."""
        if (
            self._api is None
            or self._installation_id is None
            or self._gateway_serial is None
        ):
            return self.async_abort(reason="unknown")
        if not self._devices:
            try:
                devices = await self._api.async_get_heating_devices(
                    self._installation_id, self._gateway_serial
                )
            except ViessmannApiError:
                _LOGGER.exception("Could not discover Viessmann heating devices")
                return self.async_abort(reason="cannot_connect")
            self._devices = {
                identifier: item
                for item in devices
                if (identifier := item_id(item, "id", "deviceId")) is not None
            }
            if not self._devices:
                return self.async_abort(reason="no_heating_devices")

        if user_input is None and len(self._devices) > 1:
            return self.async_show_form(
                step_id="device",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_DEVICE_ID): vol.In(
                            {
                                key: _item_label(value, key, "modelId", "model", "name")
                                for key, value in self._devices.items()
                            }
                        )
                    }
                ),
            )

        device_id = (
            user_input[CONF_DEVICE_ID]
            if user_input is not None
            else next(iter(self._devices))
        )
        device = self._devices[device_id]
        serial = item_id(device, "serial", "deviceSerial")
        model = item_id(device, "modelId", "model", "name")
        target = Target(
            self._installation_id,
            self._gateway_serial,
            device_id,
            serial,
            model,
        )
        try:
            await self._api.async_validate_target(target)
        except ViessmannApiInvalidDataError:
            return self.async_abort(reason="invalid_api_data")
        except ViessmannApiNotSupportedError:
            return self.async_abort(reason="schedule_not_supported")
        except ViessmannApiAuthenticationError:
            return self.async_abort(reason="authentication_error")
        except ViessmannApiError:
            return self.async_abort(reason="cannot_connect")

        unique_id = f"{self._installation_id}:{self._gateway_serial}:{device_id}"
        await self.async_set_unique_id(unique_id)
        if self._reconfigure_entry is None:
            self._abort_if_unique_id_configured()
        else:
            existing = next(
                (
                    entry
                    for entry in self._async_current_entries()
                    if entry.unique_id == unique_id
                    and entry.entry_id != self._reconfigure_entry.entry_id
                ),
                None,
            )
            if existing is not None:
                return self.async_abort(reason="already_configured")

            return self.async_update_reload_and_abort(
                self._reconfigure_entry,
                unique_id=unique_id,
                title=model or NAME,
                data={
                    **self._reconfigure_entry.data,
                    CONF_INSTALLATION_ID: self._installation_id,
                    CONF_GATEWAY_SERIAL: self._gateway_serial,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_SERIAL: serial,
                    CONF_DEVICE_MODEL: model,
                },
                reason="reconfigure_successful",
            )

        return self.async_create_entry(
            title=model or NAME,
            data={
                **self._oauth_data,
                CONF_INSTALLATION_ID: self._installation_id,
                CONF_GATEWAY_SERIAL: self._gateway_serial,
                CONF_DEVICE_ID: device_id,
                CONF_DEVICE_SERIAL: serial,
                CONF_DEVICE_MODEL: model,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to reauthenticate."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rediscover and select the target installation, gateway, and device."""
        self._reconfigure_entry = self._get_reconfigure_entry()
        try:
            implementation = (
                await config_entry_oauth2_flow.async_get_config_entry_implementation(
                    self.hass, self._reconfigure_entry
                )
            )
        except (
            config_entry_oauth2_flow.ImplementationUnavailableError,
            ValueError,
        ):
            return self.async_abort(reason="oauth_implementation_unavailable")

        oauth_session = config_entry_oauth2_flow.OAuth2Session(
            self.hass, self._reconfigure_entry, implementation
        )
        self._api = ViessmannApiClient(oauth_session)
        return await self._async_start_target_discovery()


def _item_label(item: Mapping[str, Any], fallback: str, *keys: str) -> str:
    """Create a readable, non-secret selection label."""
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return fallback
