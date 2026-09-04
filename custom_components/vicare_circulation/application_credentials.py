"""Application credentials platform for ViCare Circulation."""

from typing import override

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2ImplementationWithPkce,
)

from .const import AUTHORIZE_URL, OAUTH_SCOPES, TOKEN_URL


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return links and values shown in the credentials dialog."""
    return {
        "more_info_url": "https://github.com/skoeber/ha-vicare-circulation#oauth-client",
        "redirect_url": "https://my.home-assistant.io/redirect/oauth",
    }


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> "ViCareCirculationOAuth2Implementation":
    """Build a PKCE OAuth implementation for a user-provided client ID."""
    return ViCareCirculationOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        AUTHORIZE_URL,
        TOKEN_URL,
    )


class ViCareCirculationOAuth2Implementation(LocalOAuth2ImplementationWithPkce):
    """Viessmann OAuth implementation with PKCE and required scopes."""

    @property
    @override
    def extra_authorize_data(self) -> dict:
        """Append PKCE values and Viessmann scopes to the authorization URL."""
        return super().extra_authorize_data | {"scope": " ".join(OAUTH_SCOPES)}
