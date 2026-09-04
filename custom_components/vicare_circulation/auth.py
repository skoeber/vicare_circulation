"""OAuth session helpers for ViCare Circulation."""

from typing import Any

from aiohttp import ClientResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow


class RefreshingOAuthSession:
    """Delegate requests to HA and support one forced token refresh."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize the session wrapper."""
        self._hass = hass
        self._entry = entry
        self._session = session

    async def async_request(
        self, method: str, url: str, **kwargs: Any
    ) -> ClientResponse:
        """Perform an authenticated request."""
        return await self._session.async_request(method, url, **kwargs)

    async def async_force_refresh(self) -> None:
        """Expire the access token locally and refresh it through Home Assistant."""
        token = {**self._entry.data["token"], "expires_at": 0}
        self._hass.config_entries.async_update_entry(
            self._entry,
            data={**self._entry.data, "token": token},
        )
        await self._session.async_ensure_token_valid()
